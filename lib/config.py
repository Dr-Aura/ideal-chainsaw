"""Central configuration — env vars override defaults; secrets stay out of source."""

from __future__ import annotations

import os
from pathlib import Path

# Paths
APP_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("CHAINSAW_DATA_DIR", str(APP_ROOT / "data")))
CHATS_FILE = DATA_DIR / "chats.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
SECRETS_FILE = APP_ROOT / ".streamlit" / "secrets.toml"

# Models
FALLBACK_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
]
EMBEDDING_MODEL = os.getenv("CHAINSAW_EMBEDDING_MODEL", "nomic-embed-text-v1_5")
WHISPER_MODEL = os.getenv("CHAINSAW_WHISPER_MODEL", "whisper-large-v3-turbo")

# Limits (production guards)
MAX_USER_MESSAGE_CHARS = int(os.getenv("CHAINSAW_MAX_MSG_CHARS", "12000"))
MAX_MESSAGES_PER_CHAT = int(os.getenv("CHAINSAW_MAX_MESSAGES", "200"))
MAX_CHATS = int(os.getenv("CHAINSAW_MAX_CHATS", "50"))
EMBED_BATCH_SIZE = 32
TOKEN_WARN = int(os.getenv("CHAINSAW_TOKEN_WARN", "6000"))
TOKEN_HARD = int(os.getenv("CHAINSAW_TOKEN_HARD", "10000"))

# Groq client
GROQ_MAX_RETRIES = int(os.getenv("CHAINSAW_GROQ_RETRIES", "5"))
GROQ_TIMEOUT_S = float(os.getenv("CHAINSAW_GROQ_TIMEOUT", "90"))

# System presets
SYSTEM_PRESETS: dict[str, str] = {
    "Helpful": (
        "You are a helpful AI assistant. Reply clearly and accurately in English."
    ),
    "Engineer": (
        "You are a senior software engineer. Prefer precise technical answers, "
        "code examples, and trade-offs. Reply in English."
    ),
    "Teacher": (
        "You are a patient teacher. Explain concepts step by step with simple "
        "analogies. Reply in English."
    ),
    "Concise": (
        "You are a concise assistant. Answer in as few words as possible while "
        "remaining correct. Reply in English."
    ),
    "Creative": (
        "You are a creative writing partner. Be imaginative, vivid, and playful. "
        "Reply in English."
    ),
    "Custom": "",
}

DEFAULT_SETTINGS: dict = {
    "theme": "light",
    "system_preset": "Helpful",
    "custom_system": SYSTEM_PRESETS["Helpful"],
    "user_profile": "",
    "enable_search": False,
}

_PLACEHOLDER_FRAGMENTS = (
    "your_actual_private_key",
    "your_real_key",
    "your_key_here",
    "gsk_...",
    "gsk_your",
    "changeme",
    "placeholder",
)


def _is_placeholder(key: str) -> bool:
    k = key.strip().lower()
    if not k.startswith("gsk_"):
        return True
    if len(k) < 20:
        return True
    return any(p in k for p in _PLACEHOLDER_FRAGMENTS)


def get_api_key() -> str | None:
    """Resolve API key from Streamlit secrets or environment. Rejects placeholders."""
    candidates: list[str] = []

    try:
        import streamlit as st

        if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
            raw = st.secrets["GROQ_API_KEY"]
            if raw is not None:
                candidates.append(str(raw).strip())
    except Exception:
        pass

    env = os.getenv("GROQ_API_KEY", "").strip()
    if env:
        candidates.append(env)

    for key in candidates:
        if key and not _is_placeholder(key):
            return key
    return None


def secrets_help_text() -> str:
    return (
        f"Create or edit this file:\n\n`{SECRETS_FILE}`\n\n"
        "With exactly:\n\n"
        "```toml\n"
        'GROQ_API_KEY = "gsk_your_real_key_from_console.groq.com"\n'
        "```\n\n"
        "Or run: `export GROQ_API_KEY=gsk_...` then restart the app.\n\n"
        "Do **not** name a file after the key. The filename must be `secrets.toml`."
    )
