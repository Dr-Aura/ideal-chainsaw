"""ideal-chainsaw — production Streamlit UI."""

from __future__ import annotations

import logging
import sys

import numpy as np
import plotly.express as px
import streamlit as st

from lib.clustering import name_clusters, run_kmeans
from lib.config import (
    MAX_MESSAGES_PER_CHAT,
    MAX_USER_MESSAGE_CHARS,
    SYSTEM_PRESETS,
    TOKEN_HARD,
    TOKEN_WARN,
    get_api_key,
)
from lib.groq_ops import (
    build_system_prompt,
    list_chat_models,
    make_client,
    stream_chat,
    summarize_messages,
    transcribe,
)
from lib.search import is_available as search_available
from lib.search import search as web_search
from lib.search import should_search
from lib.storage import (
    empty_chat,
    estimate_tokens,
    export_markdown,
    load_chats,
    load_settings,
    new_id,
    now_iso,
    save_chats,
    save_settings,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("chainsaw.app")

st.set_page_config(
    page_title="ideal-chainsaw",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

LIGHT_CSS = """
<style>
.stApp{background:#f8f9fa!important;color:#1a1a1a!important;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
section[data-testid="stSidebar"]{background:#e9ecef!important;border-right:1px solid #dee2e6!important}
.block-container{max-width:960px!important;padding-left:1.5rem!important;padding-right:1.5rem!important}
h1,h2,h3{color:#111!important;font-weight:700!important}
.stChatMessage{background:#fff!important;border:1px solid #dee2e6!important;border-radius:8px!important;padding:1rem!important;margin-bottom:.5rem!important;color:#212529!important;box-shadow:0 1px 3px rgba(0,0,0,.05)!important}
div[data-testid="stChatInput"]{background:#fff!important;border-top:1px solid #dee2e6!important}
.token-ok{color:#198754}.token-warn{color:#fd7e14}.token-hot{color:#dc3545;font-weight:600}
</style>
"""

DARK_CSS = """
<style>
.stApp{background:#121212!important;color:#e8e8e8!important;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
section[data-testid="stSidebar"]{background:#1e1e1e!important;border-right:1px solid #333!important}
.block-container{max-width:960px!important;padding-left:1.5rem!important;padding-right:1.5rem!important}
h1,h2,h3{color:#f0f0f0!important;font-weight:700!important}
.stChatMessage{background:#1e1e1e!important;border:1px solid #333!important;border-radius:8px!important;padding:1rem!important;margin-bottom:.5rem!important;color:#e8e8e8!important;box-shadow:0 1px 3px rgba(0,0,0,.3)!important}
div[data-testid="stChatInput"]{background:#1e1e1e!important;border-top:1px solid #333!important}
.token-ok{color:#75b798}.token-warn{color:#ffc107}.token-hot{color:#ea868f;font-weight:600}
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li{color:#e8e8e8!important}
</style>
"""

# ---------------------------------------------------------------------------
# Auth + client
# ---------------------------------------------------------------------------
api_key = get_api_key()
if not api_key:
    st.error(
        "Missing **GROQ_API_KEY**. Add it under Streamlit Secrets or set the "
        "`GROQ_API_KEY` environment variable."
    )
    st.stop()

client = make_client(api_key)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_models(_key: str) -> list[str]:
    return list_chat_models(client)


# ---------------------------------------------------------------------------
# Session bootstrap
# ---------------------------------------------------------------------------
if "settings" not in st.session_state:
    st.session_state.settings = load_settings()
if "chats" not in st.session_state:
    st.session_state.chats = load_chats()

if not st.session_state.chats:
    cid = new_id()
    st.session_state.chats[cid] = empty_chat()
    st.session_state.current_chat_id = cid
    save_chats(st.session_state.chats)
elif (
    "current_chat_id" not in st.session_state
    or st.session_state.current_chat_id not in st.session_state.chats
):
    st.session_state.current_chat_id = next(iter(st.session_state.chats))

settings = st.session_state.settings
theme = settings.get("theme", "light")
st.markdown(DARK_CSS if theme == "dark" else LIGHT_CSS, unsafe_allow_html=True)

available_models = cached_models(api_key)


def persist_chat() -> None:
    save_chats(st.session_state.chats)


def non_system(messages: list[dict]) -> list[dict]:
    return [m for m in messages if m.get("role") != "system"]


def api_messages(system: str, messages: list[dict]) -> list[dict]:
    out = [{"role": "system", "content": system}]
    for m in messages:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            out.append({"role": m["role"], "content": m["content"]})
    return out


def run_stream(model: str, msgs: list[dict], temperature: float) -> str:
    return st.write_stream(stream_chat(client, model=model, messages=msgs, temperature=temperature))


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("⚙️ ideal-chainsaw")

    theme_choice = st.radio(
        "Theme", ["light", "dark"], index=0 if theme == "light" else 1, horizontal=True
    )
    if theme_choice != theme:
        settings["theme"] = theme_choice
        save_settings(settings)
        st.rerun()

    st.markdown("---")
    st.subheader("💬 Chats")
    if st.button("➕ New chat", use_container_width=True):
        cid = new_id()
        st.session_state.chats[cid] = empty_chat()
        st.session_state.current_chat_id = cid
        st.session_state.pop("cluster_result", None)
        persist_chat()
        st.rerun()

    for cid in sorted(
        st.session_state.chats.keys(),
        key=lambda i: st.session_state.chats[i].get("updated_at", ""),
        reverse=True,
    ):
        chat = st.session_state.chats[cid]
        title = (chat.get("title") or "Untitled")[:28]
        mark = "▶ " if cid == st.session_state.current_chat_id else ""
        c1, c2 = st.columns([0.78, 0.22])
        with c1:
            if st.button(f"{mark}{title}", key=f"sel_{cid}", use_container_width=True):
                st.session_state.current_chat_id = cid
                st.session_state.pop("cluster_result", None)
                st.rerun()
        with c2:
            if st.button("🗑", key=f"del_{cid}", help="Delete"):
                del st.session_state.chats[cid]
                if not st.session_state.chats:
                    nid = new_id()
                    st.session_state.chats[nid] = empty_chat()
                    st.session_state.current_chat_id = nid
                elif st.session_state.current_chat_id == cid:
                    st.session_state.current_chat_id = next(iter(st.session_state.chats))
                persist_chat()
                st.rerun()

    st.markdown("---")
    st.subheader("🧠 Model")
    model_option = st.selectbox("Primary model", available_models, index=0)
    compare_mode = st.checkbox("Multi-model compare", value=False)
    model_b = None
    if compare_mode:
        opts_b = [m for m in available_models if m != model_option] or available_models
        model_b = st.selectbox("Second model", opts_b, index=0)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)

    st.markdown("---")
    st.subheader("📝 System & profile")
    preset_keys = list(SYSTEM_PRESETS.keys())
    cur_preset = settings.get("system_preset", "Helpful")
    preset = st.selectbox(
        "System preset",
        preset_keys,
        index=preset_keys.index(cur_preset) if cur_preset in preset_keys else 0,
    )
    if preset == "Custom":
        custom_sys = st.text_area(
            "Custom system prompt",
            value=settings.get("custom_system", ""),
            height=100,
            max_chars=4000,
        )
    else:
        custom_sys = SYSTEM_PRESETS[preset]
        st.caption(custom_sys[:140] + ("…" if len(custom_sys) > 140 else ""))

    profile = st.text_area(
        "About you (always in context)",
        value=settings.get("user_profile", ""),
        height=80,
        max_chars=2000,
        placeholder="e.g. Python developer, prefer short answers…",
    )
    enable_search = st.checkbox(
        "Enable web search",
        value=settings.get("enable_search", False),
        disabled=not search_available(),
        help="Requires duckduckgo-search package",
    )

    if (
        preset != settings.get("system_preset")
        or custom_sys != settings.get("custom_system")
        or profile != settings.get("user_profile")
        or enable_search != settings.get("enable_search")
    ):
        settings.update(
            {
                "system_preset": preset,
                "custom_system": custom_sys,
                "user_profile": profile,
                "enable_search": enable_search,
            }
        )
        st.session_state.settings = settings
        save_settings(settings)

    st.markdown("---")
    st.subheader("📊 Topic clustering")
    cluster_scope = st.radio("Scope", ["Current chat", "All chats"], horizontal=True)
    cur_msgs = st.session_state.chats[st.session_state.current_chat_id]["messages"]
    if cluster_scope == "Current chat":
        msgs_for_cluster = non_system(cur_msgs)
    else:
        msgs_for_cluster = []
        for c in st.session_state.chats.values():
            msgs_for_cluster.extend(non_system(c.get("messages", [])))

    n_msgs = len(msgs_for_cluster)
    if n_msgs < 4:
        st.info("Need ≥ 4 messages to cluster.")
    else:
        max_k = min(8, max(2, n_msgs // 2))
        n_clusters = st.slider("K (topics)", 2, max_k, min(3, max_k))
        if st.button("🔍 Run K-means", use_container_width=True):
            with st.spinner("Embedding & clustering…"):
                try:
                    texts = [
                        f"{m['role'].upper()}: {m['content'][:800]}" for m in msgs_for_cluster
                    ]
                    emb2d, labels, sizes = run_kmeans(client, texts, n_clusters)
                    names = name_clusters(client, model_option, texts, labels, n_clusters)
                    st.session_state["cluster_result"] = {
                        "texts": texts,
                        "labels": labels.tolist(),
                        "embeddings_2d": emb2d.tolist(),
                        "names": names,
                        "sizes": sizes,
                        "n_clusters": n_clusters,
                    }
                    st.success(f"{n_clusters} topics found")
                except Exception as e:
                    log.exception("clustering failed")
                    st.error(f"Clustering failed: {type(e).__name__}: {e}")

    st.markdown("---")
    cur = st.session_state.chats[st.session_state.current_chat_id]
    md = export_markdown(cur.get("title", "chat"), cur.get("messages", []))
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in (cur.get("title") or "chat")[:40])
    st.download_button(
        "⬇️ Export chat (Markdown)",
        data=md,
        file_name=f"{safe_name or 'chat'}.md",
        mime="text/markdown",
        use_container_width=True,
    )
    if st.button("🧹 Clear current chat", use_container_width=True):
        cur["messages"] = []
        cur["updated_at"] = now_iso()
        persist_chat()
        st.session_state.pop("cluster_result", None)
        st.rerun()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
chat = st.session_state.chats[st.session_state.current_chat_id]
messages = chat["messages"]

new_title = st.text_input(
    "Chat title",
    value=chat.get("title", "New chat"),
    label_visibility="collapsed",
    placeholder="Chat title…",
    max_chars=120,
)
if new_title and new_title != chat.get("title"):
    chat["title"] = new_title
    chat["updated_at"] = now_iso()
    persist_chat()

tokens = estimate_tokens(messages)
token_class = "token-ok" if tokens < TOKEN_WARN else ("token-warn" if tokens < TOKEN_HARD else "token-hot")
st.caption(
    f"Groq · `{model_option}` · temp {temperature} · "
    f"context <span class='{token_class}'>~{tokens} tokens</span>"
    + (" · compare" if compare_mode else ""),
    unsafe_allow_html=True,
)

if tokens >= TOKEN_WARN and len(non_system(messages)) > 4:
    if st.button("✂️ Summarize older messages (free context)"):
        keep = messages[-4:]
        old = [m for m in messages[:-4] if m.get("role") != "system"]
        summary = summarize_messages(client, model_option, old)
        chat["messages"] = [
            {"role": "system", "content": f"[Earlier conversation summary]\n{summary}"}
        ] + keep
        chat["updated_at"] = now_iso()
        persist_chat()
        st.rerun()

system_content = build_system_prompt(preset, custom_sys, profile, enable_search)

for idx, message in enumerate(messages):
    role = message.get("role")
    if role == "system":
        with st.expander("System / summary context", expanded=False):
            st.markdown(message.get("content", ""))
        continue
    with st.chat_message(role):
        st.markdown(message.get("content", ""))
        if role == "assistant":
            a1, a2, a3, a4, a5, a6 = st.columns(6)
            if a1.button("🔄", key=f"regen_{idx}", help="Regenerate"):
                st.session_state["_action"] = {"type": "regen", "idx": idx}
                st.rerun()
            if a2.button("➡️", key=f"cont_{idx}", help="Continue"):
                st.session_state["_action"] = {"type": "continue", "idx": idx}
                st.rerun()
            if a3.button("📉", key=f"short_{idx}", help="Shorter"):
                st.session_state["_action"] = {"type": "style", "idx": idx, "style": "shorter"}
                st.rerun()
            if a4.button("📈", key=f"long_{idx}", help="Longer"):
                st.session_state["_action"] = {"type": "style", "idx": idx, "style": "longer"}
                st.rerun()
            if a5.button("👔", key=f"formal_{idx}", help="More formal"):
                st.session_state["_action"] = {
                    "type": "style",
                    "idx": idx,
                    "style": "more formal",
                }
                st.rerun()
            a6.download_button(
                "📋",
                data=message.get("content", ""),
                file_name="reply.md",
                mime="text/markdown",
                key=f"dl_{idx}",
                help="Download reply",
            )

# Message actions
if "_action" in st.session_state:
    action = st.session_state.pop("_action")
    idx = int(action["idx"])
    if action["type"] == "regen" and 0 <= idx < len(messages):
        chat["messages"] = messages[:idx]
        msgs = api_messages(system_content, chat["messages"])
        with st.chat_message("assistant"):
            if compare_mode and model_b:
                c1, c2 = st.columns(2)
                with c1:
                    st.caption(model_option)
                    r1 = run_stream(model_option, msgs, temperature)
                with c2:
                    st.caption(model_b)
                    r2 = run_stream(model_b, msgs, temperature)
                full = f"**{model_option}:**\n{r1}\n\n---\n\n**{model_b}:**\n{r2}"
            else:
                full = run_stream(model_option, msgs, temperature)
            chat["messages"].append({"role": "assistant", "content": full or ""})
            chat["updated_at"] = now_iso()
            persist_chat()

    elif action["type"] == "continue":
        msgs = api_messages(system_content, messages)
        msgs.append({"role": "user", "content": "Please continue from where you left off."})
        with st.chat_message("assistant"):
            full = run_stream(model_option, msgs, temperature)
            chat["messages"].append({"role": "assistant", "content": full or ""})
            chat["updated_at"] = now_iso()
            persist_chat()

    elif action["type"] == "style" and 0 <= idx < len(messages):
        original = messages[idx].get("content", "")
        style = action["style"]
        msgs = [
            {"role": "system", "content": system_content},
            {
                "role": "user",
                "content": f"Rewrite the following reply to be {style}. Keep the same meaning.\n\n{original[:8000]}",
            },
        ]
        with st.chat_message("assistant"):
            full = run_stream(model_option, msgs, temperature)
            chat["messages"][idx] = {"role": "assistant", "content": full or original}
            chat["updated_at"] = now_iso()
            persist_chat()
            st.rerun()

# Voice
audio = st.audio_input("🎤 Voice message (optional)")
voice_text = None
if audio is not None:
    raw = audio.getvalue() if hasattr(audio, "getvalue") else audio.read()
    with st.spinner("Transcribing…"):
        voice_text = transcribe(client, raw, getattr(audio, "name", "audio.wav"))
    if voice_text and not voice_text.startswith("[transcription"):
        st.info(f"Transcribed: {voice_text[:300]}{'…' if len(voice_text) > 300 else ''}")

prompt = st.chat_input("What is on your mind?")
if voice_text and not voice_text.startswith("[transcription") and not prompt:
    prompt = voice_text

if prompt:
    prompt = prompt.strip()[:MAX_USER_MESSAGE_CHARS]
    if not prompt:
        st.warning("Empty message.")
        st.stop()

    if len(messages) >= MAX_MESSAGES_PER_CHAT:
        st.warning(
            f"This chat hit the {MAX_MESSAGES_PER_CHAT}-message limit. "
            "Summarize older messages or start a new chat."
        )
        st.stop()

    extra = ""
    if enable_search and search_available() and should_search(prompt):
        with st.spinner("Searching the web…"):
            extra = web_search(prompt)

    chat["messages"].append({"role": "user", "content": prompt})
    if chat.get("title") in ("New chat", "Untitled", "") and len(non_system(chat["messages"])) == 1:
        chat["title"] = prompt[:48] + ("…" if len(prompt) > 48 else "")

    with st.chat_message("user"):
        st.markdown(prompt)
        if extra:
            with st.expander("Web search results used"):
                st.markdown(extra)

    msgs = api_messages(system_content, chat["messages"])
    if extra:
        # Insert search context before the latest user turn
        msgs.insert(-1, {"role": "system", "content": f"[WEB SEARCH]\n{extra[:6000]}"})

    with st.chat_message("assistant"):
        if compare_mode and model_b:
            c1, c2 = st.columns(2)
            with c1:
                st.caption(model_option)
                r1 = run_stream(model_option, msgs, temperature)
            with c2:
                st.caption(model_b)
                r2 = run_stream(model_b, msgs, temperature)
            full = f"**{model_option}:**\n{r1}\n\n---\n\n**{model_b}:**\n{r2}"
        else:
            full = run_stream(model_option, msgs, temperature)
        chat["messages"].append({"role": "assistant", "content": full or ""})
        chat["updated_at"] = now_iso()
        persist_chat()

# Clusters
if "cluster_result" in st.session_state:
    result = st.session_state["cluster_result"]
    st.markdown("---")
    st.subheader("📊 Topic clusters")
    emb = np.array(result["embeddings_2d"])
    labels = np.array(result["labels"])
    names = result["names"]
    fig = px.scatter(
        x=emb[:, 0],
        y=emb[:, 1],
        color=[names[l] for l in labels],
        hover_data={"text": result["texts"]},
        labels={"x": "PCA 1", "y": "PCA 2", "color": "Topic"},
        title="Embeddings (PCA 2D)",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(marker=dict(size=11, opacity=0.85))
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
    cols = st.columns(min(3, result["n_clusters"]))
    for i, name in enumerate(names):
        with cols[i % len(cols)]:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.caption(f"{result['sizes'][i]} message(s)")
                members = [
                    result["texts"][j]
                    for j in range(len(result["texts"]))
                    if result["labels"][j] == i
                ]
                for m in members[:3]:
                    st.markdown(f"- _{m[:120]}{'…' if len(m) > 120 else ''}_")
                if len(members) > 3:
                    st.caption(f"+ {len(members) - 3} more")
