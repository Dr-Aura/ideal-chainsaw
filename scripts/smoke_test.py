#!/usr/bin/env python3
"""Verify secrets + a live Groq chat model. Run from anywhere:

  /path/to/ai-env/bin/python /path/to/scripts/smoke_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

from groq import Groq

SECRETS = ROOT / ".streamlit" / "secrets.toml"
CANDIDATES = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
]


def main() -> int:
    if not SECRETS.is_file():
        print(f"FAIL: missing {SECRETS}")
        print('  Create it with: GROQ_API_KEY = "gsk_..."')
        return 1

    data = tomllib.loads(SECRETS.read_text())
    key = str(data.get("GROQ_API_KEY", "")).strip()
    if not key.startswith("gsk_") or len(key) < 20:
        print("FAIL: GROQ_API_KEY missing or looks invalid in secrets.toml")
        return 1
    print(f"OK key loaded (len={len(key)})")

    client = Groq(api_key=key)
    try:
        ids = [m.id for m in client.models.list().data]
        print(f"OK models.list() → {len(ids)} models")
    except Exception as e:
        print(f"FAIL models.list: {e}")
        return 1

    chat_ids = [
        i
        for i in ids
        if not any(x in i.lower() for x in ("whisper", "embed", "guard", "tts", "orpheus"))
    ]
    preferred = [m for m in CANDIDATES if m in chat_ids] or chat_ids[:3]
    if not preferred:
        print("FAIL: no chat models available on this key/plan")
        return 1

    model = preferred[0]
    print(f"Trying chat: {model}")
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: pong"}],
            max_tokens=16,
        )
        text = (r.choices[0].message.content or "").strip()
        print(f"OK chat reply: {text!r}")
    except Exception as e:
        print(f"FAIL chat: {e}")
        print("Available chat-ish models:")
        for i in sorted(chat_ids)[:20]:
            print(f"  {i}")
        return 1

    print("\nSMOKE TEST PASSED — use this model in the app sidebar:")
    print(f"  {model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
