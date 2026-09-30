"""Durable local JSON storage with safe writes and migration."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.config import CHATS_FILE, DATA_DIR, DEFAULT_SETTINGS, MAX_CHATS, SETTINGS_FILE

log = logging.getLogger("chainsaw.storage")


def _ensure_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_write(path: Path, data: dict | list) -> None:
    """Write JSON atomically to avoid corruption on crash."""
    _ensure_dir()
    fd, tmp = tempfile.mkstemp(dir=str(DATA_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("Failed to read %s: %s — using defaults", path, e)
        return default


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return uuid.uuid4().hex[:10]


def load_chats() -> dict[str, dict]:
    raw = _read_json(CHATS_FILE, {})
    if not isinstance(raw, dict):
        return {}
    return raw


def save_chats(chats: dict[str, dict]) -> None:
    # Cap total chats (drop oldest by updated_at)
    if len(chats) > MAX_CHATS:
        ordered = sorted(chats.items(), key=lambda kv: kv[1].get("updated_at", ""))
        for cid, _ in ordered[: len(chats) - MAX_CHATS]:
            chats.pop(cid, None)
            log.info("Pruned old chat %s (max %s)", cid, MAX_CHATS)
    try:
        _atomic_write(CHATS_FILE, chats)
    except OSError as e:
        log.error("Cannot persist chats (read-only FS?): %s", e)


def load_settings() -> dict:
    data = _read_json(SETTINGS_FILE, {})
    out = dict(DEFAULT_SETTINGS)
    if isinstance(data, dict):
        out.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS or k in data})
    return out


def save_settings(settings: dict) -> None:
    try:
        _atomic_write(SETTINGS_FILE, settings)
    except OSError as e:
        log.error("Cannot persist settings: %s", e)


def empty_chat(title: str = "New chat") -> dict:
    ts = now_iso()
    return {"title": title, "messages": [], "created_at": ts, "updated_at": ts}


def export_markdown(title: str, messages: list[dict]) -> str:
    lines = [
        f"# {title}",
        "",
        f"_Exported {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
    ]
    for m in messages:
        if m.get("role") == "system":
            continue
        role = "You" if m.get("role") == "user" else "Assistant"
        lines.append(f"## {role}")
        lines.append(m.get("content", ""))
        lines.append("")
    return "\n".join(lines)


def estimate_tokens(messages: list[dict]) -> int:
    return sum(max(1, len(m.get("content", "")) // 4) for m in messages)
