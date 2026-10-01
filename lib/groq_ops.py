"""Groq client wrappers with retries, filtering, and safe streaming."""

from __future__ import annotations

import logging
from typing import Generator, Iterable

import numpy as np
from groq import APIConnectionError, APIStatusError, Groq, RateLimitError

from lib.config import (
    EMBED_BATCH_SIZE,
    EMBEDDING_MODEL,
    FALLBACK_MODELS,
    GROQ_MAX_RETRIES,
    GROQ_TIMEOUT_S,
    SYSTEM_PRESETS,
    WHISPER_MODEL,
)

log = logging.getLogger("chainsaw.groq")

_NON_CHAT_HINTS = ("whisper", "embed", "guard", "tts", "orpheus", "prompt-guard")

# Retired for free/developer tier (2026-08). Still listed by some APIs — hide them.
_DEPRECATED_MODELS = frozenset(
    {
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "gemma2-9b-it",
        "gemma-7b-it",
        "mixtral-8x7b-32768",
        "llama3-8b-8192",
        "llama3-70b-8192",
    }
)

_PREFERRED_PREFIXES = ("openai/gpt-oss", "qwen/", "meta-llama/llama-4")


def make_client(api_key: str) -> Groq:
    return Groq(
        api_key=api_key,
        max_retries=GROQ_MAX_RETRIES,
        timeout=GROQ_TIMEOUT_S,
    )


def list_chat_models(client: Groq) -> list[str]:
    try:
        models = client.models.list()
        ids = [
            m.id
            for m in models.data
            if getattr(m, "active", True)
            and m.id not in _DEPRECATED_MODELS
            and not any(h in m.id.lower() for h in _NON_CHAT_HINTS)
        ]
        if not ids:
            return list(FALLBACK_MODELS)

        def sort_key(mid: str) -> tuple:
            preferred = 0 if any(mid.startswith(p) for p in _PREFERRED_PREFIXES) else 1
            return (preferred, mid)

        return sorted(ids, key=sort_key)
    except Exception as e:
        log.warning("model list failed: %s", e)
        return list(FALLBACK_MODELS)


def get_embeddings(client: Groq, texts: list[str]) -> np.ndarray:
    if not texts:
        return np.array([])
    all_emb: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i : i + EMBED_BATCH_SIZE]
        batch = [t[:8000] for t in batch]
        try:
            resp = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
                encoding_format="float",
            )
            ordered = sorted(resp.data, key=lambda x: x.index)
            all_emb.extend([d.embedding for d in ordered])
        except (RateLimitError, APIConnectionError, APIStatusError) as e:
            log.error("embedding batch failed: %s", e)
            raise
    return np.array(all_emb)


def stream_chat(
    client: Groq,
    *,
    model: str,
    messages: list[dict],
    temperature: float,
) -> Generator[str, None, None]:
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta.content
            except (IndexError, AttributeError):
                continue
            if delta:
                yield delta
    except RateLimitError:
        yield "⚠️ Rate limit reached. Please wait a moment and try again."
        log.warning("rate limit on model=%s", model)
    except APIConnectionError as e:
        yield "⚠️ Network error talking to Groq. Check your connection."
        log.error("connection error: %s", e)
    except APIStatusError as e:
        msg = str(getattr(e, "message", "") or e)
        if e.status_code == 404 or "model_not_found" in msg.lower() or "does not exist" in msg.lower():
            yield (
                f"⚠️ Model `{model}` is not available on your Groq plan. "
                "Pick **openai/gpt-oss-20b** (or another model) in the sidebar."
            )
        else:
            yield f"⚠️ API error ({e.status_code}). Try another model or retry."
        log.error("api status %s model=%s: %s", e.status_code, model, e)
    except Exception as e:
        yield f"⚠️ Unexpected error: {type(e).__name__}"
        log.exception("stream_chat failed")


def complete_once(
    client: Groq,
    *,
    model: str,
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 400,
) -> str:
    try:
        r = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (r.choices[0].message.content or "").strip()
    except Exception as e:
        log.error("complete_once failed: %s", e)
        return ""


def transcribe(client: Groq, audio_bytes: bytes, filename: str = "audio.wav") -> str:
    try:
        result = client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model=WHISPER_MODEL,
            response_format="text",
        )
        if isinstance(result, str):
            return result.strip()
        return (getattr(result, "text", None) or str(result)).strip()
    except Exception as e:
        log.error("transcription failed: %s", e)
        return f"[transcription error: {type(e).__name__}]"


def build_system_prompt(
    preset: str,
    custom: str,
    profile: str,
    enable_search: bool,
) -> str:
    base = custom if preset == "Custom" else SYSTEM_PRESETS.get(preset, SYSTEM_PRESETS["Helpful"])
    parts = [base]
    if profile.strip():
        parts.append(f"User profile / preferences:\n{profile.strip()[:2000]}")
    if enable_search:
        parts.append(
            "You may receive [WEB SEARCH] results. Use them when relevant and cite briefly."
        )
    return "\n\n".join(parts)


def summarize_messages(client: Groq, model: str, messages: Iterable[dict]) -> str:
    text = "\n".join(
        f"{m.get('role')}: {m.get('content', '')[:500]}"
        for m in messages
        if m.get("role") != "system"
    )[:12000]
    out = complete_once(
        client,
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Summarize this conversation in 5-8 bullet points. Keep key facts and decisions.",
            },
            {"role": "user", "content": text},
        ],
        temperature=0.2,
        max_tokens=400,
    )
    return out or "(summary unavailable)"
