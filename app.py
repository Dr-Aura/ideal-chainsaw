import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import plotly.express as px
import streamlit as st
from groq import Groq
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(page_title="ideal-chainsaw", page_icon="🤖", layout="wide")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FALLBACK_MODELS = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "gemma2-9b-it"]
EMBEDDING_MODEL = "nomic-embed-text-v1_5"
WHISPER_MODEL = "whisper-large-v3-turbo"
DATA_DIR = Path(__file__).parent / "data"
CHATS_FILE = DATA_DIR / "chats.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

SYSTEM_PRESETS = {
    "Helpful": "You are a helpful AI assistant. Reply clearly and accurately in English.",
    "Engineer": "You are a senior software engineer. Prefer precise technical answers, code examples, and trade-offs. Reply in English.",
    "Teacher": "You are a patient teacher. Explain concepts step by step with simple analogies. Reply in English.",
    "Concise": "You are a concise assistant. Answer in as few words as possible while remaining correct. Reply in English.",
    "Creative": "You are a creative writing partner. Be imaginative, vivid, and playful. Reply in English.",
    "Custom": "",
}

TOKEN_WARN = 6000
TOKEN_HARD = 10000

# ---------------------------------------------------------------------------
# Theme CSS
# ---------------------------------------------------------------------------
LIGHT_CSS = """
    <style>
        .stApp { background-color: #f8f9fa !important; color: #1a1a1a !important;
                 font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        section[data-testid="stSidebar"] { background-color: #e9ecef !important; border-right: 1px solid #dee2e6 !important; }
        .block-container { max-width: 960px !important; padding-left: 1.5rem !important; padding-right: 1.5rem !important; }
        h1, h2, h3 { color: #111111 !important; font-weight: 700 !important; }
        .stChatMessage { background-color: #ffffff !important; border: 1px solid #dee2e6 !important;
                         border-radius: 8px !important; padding: 1rem !important; margin-bottom: 0.5rem !important;
                         color: #212529 !important; box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important; }
        div[data-testid="stChatInput"] { background-color: #ffffff !important; border-top: 1px solid #dee2e6 !important; }
        .token-ok { color: #198754; } .token-warn { color: #fd7e14; } .token-hot { color: #dc3545; font-weight: 600; }
    </style>
"""

DARK_CSS = """
    <style>
        .stApp { background-color: #121212 !important; color: #e8e8e8 !important;
                 font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        section[data-testid="stSidebar"] { background-color: #1e1e1e !important; border-right: 1px solid #333 !important; }
        .block-container { max-width: 960px !important; padding-left: 1.5rem !important; padding-right: 1.5rem !important; }
        h1, h2, h3 { color: #f0f0f0 !important; font-weight: 700 !important; }
        .stChatMessage { background-color: #1e1e1e !important; border: 1px solid #333 !important;
                         border-radius: 8px !important; padding: 1rem !important; margin-bottom: 0.5rem !important;
                         color: #e8e8e8 !important; box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important; }
        div[data-testid="stChatInput"] { background-color: #1e1e1e !important; border-top: 1px solid #333 !important; }
        .token-ok { color: #75b798; } .token-warn { color: #ffc107; } .token-hot { color: #ea868f; font-weight: 600; }
        [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li { color: #e8e8e8 !important; }
    </style>
"""

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
if "GROQ_API_KEY" not in st.secrets:
    st.error("Please add your GROQ_API_KEY to the Streamlit Secrets manager.")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------
def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_chats() -> dict:
    _ensure_data_dir()
    if CHATS_FILE.exists():
        try:
            return json.loads(CHATS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_chats(chats: dict) -> None:
    _ensure_data_dir()
    CHATS_FILE.write_text(json.dumps(chats, ensure_ascii=False, indent=2), encoding="utf-8")


def load_settings() -> dict:
    _ensure_data_dir()
    defaults = {
        "theme": "light",
        "system_preset": "Helpful",
        "custom_system": SYSTEM_PRESETS["Helpful"],
        "user_profile": "",
        "enable_search": False,
    }
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            defaults.update(data)
        except Exception:
            pass
    return defaults


def save_settings(settings: dict) -> None:
    _ensure_data_dir()
    SETTINGS_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def new_chat_id() -> str:
    return str(uuid.uuid4())[:8]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def estimate_tokens(messages: list[dict]) -> int:
    total = 0
    for m in messages:
        total += max(1, len(m.get("content", "")) // 4)
    return total


def export_chat_markdown(title: str, messages: list[dict]) -> str:
    lines = [f"# {title}", "", f"_Exported {datetime.now().strftime('%Y-%m-%d %H:%M')}_", ""]
    for m in messages:
        if m["role"] == "system":
            continue
        role = "You" if m["role"] == "user" else "Assistant"
        lines.append(f"## {role}")
        lines.append(m["content"])
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Models / embeddings / clustering
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_available_models(_key: str) -> list[str]:
    try:
        models = client.models.list()
        ids = [m.id for m in models.data if getattr(m, "active", True)]
        # Prefer chat models; filter obvious non-chat
        chat_ids = [
            i for i in ids
            if "whisper" not in i.lower()
            and "embed" not in i.lower()
            and "guard" not in i.lower()
            and "tts" not in i.lower()
            and "orpheus" not in i.lower()
        ]
        return sorted(chat_ids) if chat_ids else FALLBACK_MODELS
    except Exception:
        return FALLBACK_MODELS


def get_embeddings(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.array([])
    all_emb = []
    for i in range(0, len(texts), 32):
        batch = texts[i : i + 32]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch, encoding_format="float")
        sorted_data = sorted(resp.data, key=lambda x: x.index)
        all_emb.extend([d.embedding for d in sorted_data])
    return np.array(all_emb)


def run_kmeans(texts: list[str], n_clusters: int, seed: int = 42):
    emb = get_embeddings(texts)
    if len(emb) < n_clusters:
        raise ValueError(f"Need at least {n_clusters} items.")
    labels = KMeans(n_clusters=n_clusters, random_state=seed, n_init=10).fit_predict(emb)
    emb_2d = PCA(n_components=2, random_state=seed).fit_transform(emb) if emb.shape[1] > 2 else emb
    sizes = [int(np.sum(labels == i)) for i in range(n_clusters)]
    return emb_2d, labels, sizes


def label_clusters(texts: list[str], labels: np.ndarray, n: int, model: str) -> list[str]:
    names = []
    for i in range(n):
        sample = [texts[j] for j in range(len(texts)) if labels[j] == i][:5]
        prompt = (
            "Given these conversation snippets in one topic cluster, reply with ONLY a short "
            "2-5 word topic title. No quotes, no explanation.\n\n" + "\n---\n".join(sample)
        )
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You name topics concisely."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=20,
            )
            name = (r.choices[0].message.content or "").strip().strip('"').strip("'")
            names.append(name or f"Topic {i + 1}")
        except Exception:
            names.append(f"Topic {i + 1}")
    return names


def web_search(query: str, max_results: int = 5) -> str:
    if DDGS is None:
        return "Web search package not installed."
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. **{r.get('title', '')}**\n   {r.get('href', '')}\n   {r.get('body', '')}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Search error: {e}"


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    try:
        transcription = client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model=WHISPER_MODEL,
            response_format="text",
        )
        if isinstance(transcription, str):
            return transcription
        return getattr(transcription, "text", str(transcription))
    except Exception as e:
        return f"[transcription error: {e}]"


def build_system_message(preset: str, custom: str, profile: str, enable_search: bool) -> str:
    base = custom if preset == "Custom" else SYSTEM_PRESETS.get(preset, SYSTEM_PRESETS["Helpful"])
    parts = [base]
    if profile.strip():
        parts.append(f"User profile / preferences:\n{profile.strip()}")
    if enable_search:
        parts.append(
            "You may be given web search results prefixed with [WEB SEARCH]. Use them when relevant and cite sources briefly."
        )
    return "\n\n".join(parts)


def summarize_old_messages(messages: list[dict], model: str) -> str:
    """Summarize older turns to free context."""
    text = "\n".join(f"{m['role']}: {m['content'][:500]}" for m in messages if m["role"] != "system")
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Summarize this conversation in 5-8 bullet points. Keep key facts and decisions."},
                {"role": "user", "content": text[:12000]},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        return (r.choices[0].message.content or "").strip()
    except Exception as e:
        return f"(summary failed: {e})"


def stream_completion(model: str, messages: list[dict], temperature: float):
    try:
        stream = client.chat.completions.create(
            model=model, messages=messages, temperature=temperature, stream=True
        )
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except Exception as e:
        yield f"⚠️ API Error: {e}"


# ---------------------------------------------------------------------------
# Session bootstrap
# ---------------------------------------------------------------------------
if "settings" not in st.session_state:
    st.session_state.settings = load_settings()

if "chats" not in st.session_state:
    st.session_state.chats = load_chats()

if not st.session_state.chats:
    cid = new_chat_id()
    st.session_state.chats[cid] = {
        "title": "New chat",
        "messages": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    st.session_state.current_chat_id = cid
    save_chats(st.session_state.chats)
elif "current_chat_id" not in st.session_state or st.session_state.current_chat_id not in st.session_state.chats:
    st.session_state.current_chat_id = next(iter(st.session_state.chats))

settings = st.session_state.settings
theme = settings.get("theme", "light")
st.markdown(DARK_CSS if theme == "dark" else LIGHT_CSS, unsafe_allow_html=True)

available_models = fetch_available_models(st.secrets["GROQ_API_KEY"])

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("⚙️ ideal-chainsaw")

    # Theme
    theme_choice = st.radio("Theme", ["light", "dark"], index=0 if theme == "light" else 1, horizontal=True)
    if theme_choice != theme:
        settings["theme"] = theme_choice
        st.session_state.settings = settings
        save_settings(settings)
        st.rerun()

    st.markdown("---")
    st.subheader("💬 Chats")

    if st.button("➕ New chat", use_container_width=True):
        cid = new_chat_id()
        st.session_state.chats[cid] = {
            "title": "New chat",
            "messages": [],
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        st.session_state.current_chat_id = cid
        if "cluster_result" in st.session_state:
            del st.session_state["cluster_result"]
        save_chats(st.session_state.chats)
        st.rerun()

    # Chat list (most recently updated first)
    sorted_ids = sorted(
        st.session_state.chats.keys(),
        key=lambda i: st.session_state.chats[i].get("updated_at", ""),
        reverse=True,
    )
    for cid in sorted_ids:
        chat = st.session_state.chats[cid]
        title = chat.get("title") or "Untitled"
        is_current = cid == st.session_state.current_chat_id
        cols = st.columns([0.75, 0.25])
        with cols[0]:
            label = f"{'▶ ' if is_current else ''}{title[:28]}"
            if st.button(label, key=f"sel_{cid}", use_container_width=True):
                st.session_state.current_chat_id = cid
                if "cluster_result" in st.session_state:
                    del st.session_state["cluster_result"]
                st.rerun()
        with cols[1]:
            if st.button("🗑", key=f"del_{cid}", help="Delete chat"):
                del st.session_state.chats[cid]
                if not st.session_state.chats:
                    nid = new_chat_id()
                    st.session_state.chats[nid] = {
                        "title": "New chat",
                        "messages": [],
                        "created_at": now_iso(),
                        "updated_at": now_iso(),
                    }
                    st.session_state.current_chat_id = nid
                elif st.session_state.current_chat_id == cid:
                    st.session_state.current_chat_id = next(iter(st.session_state.chats))
                save_chats(st.session_state.chats)
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
    preset = st.selectbox("System preset", list(SYSTEM_PRESETS.keys()),
                          index=list(SYSTEM_PRESETS.keys()).index(settings.get("system_preset", "Helpful"))
                          if settings.get("system_preset", "Helpful") in SYSTEM_PRESETS else 0)
    if preset == "Custom":
        custom_sys = st.text_area("Custom system prompt", value=settings.get("custom_system", ""), height=100)
    else:
        custom_sys = SYSTEM_PRESETS[preset]
        st.caption(custom_sys[:120] + ("…" if len(custom_sys) > 120 else ""))

    profile = st.text_area(
        "About you (always in context)",
        value=settings.get("user_profile", ""),
        height=80,
        placeholder="e.g. Python developer, prefer short answers…",
    )
    enable_search = st.checkbox("Enable web search tool", value=settings.get("enable_search", False))

    if (preset != settings.get("system_preset") or custom_sys != settings.get("custom_system")
            or profile != settings.get("user_profile") or enable_search != settings.get("enable_search")):
        settings.update({
            "system_preset": preset,
            "custom_system": custom_sys,
            "user_profile": profile,
            "enable_search": enable_search,
        })
        st.session_state.settings = settings
        save_settings(settings)

    st.markdown("---")
    st.subheader("📊 Topic clustering")
    cluster_scope = st.radio("Scope", ["Current chat", "All chats"], horizontal=True)
    current_messages = st.session_state.chats[st.session_state.current_chat_id]["messages"]

    if cluster_scope == "Current chat":
        msgs_for_cluster = [m for m in current_messages if m["role"] != "system"]
    else:
        msgs_for_cluster = []
        for c in st.session_state.chats.values():
            msgs_for_cluster.extend([m for m in c.get("messages", []) if m["role"] != "system"])

    n_msgs = len(msgs_for_cluster)
    if n_msgs < 4:
        st.info("Need ≥ 4 messages to cluster.")
    else:
        max_k = min(8, max(2, n_msgs // 2))
        n_clusters = st.slider("K (topics)", 2, max_k, min(3, max_k))
        if st.button("🔍 Run K-means", use_container_width=True):
            with st.spinner("Embedding & clustering…"):
                try:
                    texts = [f"{m['role'].upper()}: {m['content'][:800]}" for m in msgs_for_cluster]
                    emb2d, labels, sizes = run_kmeans(texts, n_clusters)
                    names = label_clusters(texts, labels, n_clusters, model_option)
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
                    st.error(str(e))

    st.markdown("---")
    # Export current chat
    cur = st.session_state.chats[st.session_state.current_chat_id]
    md = export_chat_markdown(cur.get("title", "chat"), cur.get("messages", []))
    st.download_button(
        "⬇️ Export chat (Markdown)",
        data=md,
        file_name=f"{cur.get('title', 'chat').replace(' ', '_')[:40]}.md",
        mime="text/markdown",
        use_container_width=True,
    )

    if st.button("🧹 Clear current chat", use_container_width=True):
        st.session_state.chats[st.session_state.current_chat_id]["messages"] = []
        st.session_state.chats[st.session_state.current_chat_id]["updated_at"] = now_iso()
        save_chats(st.session_state.chats)
        if "cluster_result" in st.session_state:
            del st.session_state["cluster_result"]
        st.rerun()

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
chat = st.session_state.chats[st.session_state.current_chat_id]
messages = chat["messages"]

# Editable title
new_title = st.text_input("Chat title", value=chat.get("title", "New chat"), label_visibility="collapsed",
                          placeholder="Chat title…")
if new_title != chat.get("title"):
    chat["title"] = new_title or "Untitled"
    chat["updated_at"] = now_iso()
    save_chats(st.session_state.chats)

tokens = estimate_tokens(messages)
token_class = "token-ok" if tokens < TOKEN_WARN else ("token-warn" if tokens < TOKEN_HARD else "token-hot")
st.caption(
    f"Powered by Groq · Model: `{model_option}` · Temp: {temperature} · "
    f"Context: <span class='{token_class}'>~{tokens} tokens</span>"
    + (" · Compare mode" if compare_mode else ""),
    unsafe_allow_html=True,
)

# Smart trim button when hot
if tokens >= TOKEN_WARN:
    if st.button("✂️ Summarize older messages (free context)"):
        if len(messages) > 4:
            keep = messages[-4:]
            old = messages[:-4]
            summary = summarize_old_messages(old, model_option)
            chat["messages"] = [
                {"role": "system", "content": f"[Earlier conversation summary]\n{summary}"}
            ] + keep
            chat["updated_at"] = now_iso()
            save_chats(st.session_state.chats)
            st.rerun()

# Render messages + actions
for idx, message in enumerate(messages):
    if message["role"] == "system":
        with st.expander("System / summary context", expanded=False):
            st.markdown(message["content"])
        continue
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            a1, a2, a3, a4, a5, a6 = st.columns(6)
            if a1.button("🔄", key=f"regen_{idx}", help="Regenerate"):
                # Remove this assistant msg and the preceding user msg stays; re-ask last user
                # Find previous user message
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
                st.session_state["_action"] = {"type": "style", "idx": idx, "style": "more formal"}
                st.rerun()
            a6.download_button(
                "📋",
                data=message["content"],
                file_name="reply.md",
                mime="text/markdown",
                key=f"copy_{idx}",
                help="Download this reply",
            )

# Handle pending message actions
if "_action" in st.session_state:
    action = st.session_state.pop("_action")
    idx = action["idx"]
    system_content = build_system_message(preset, custom_sys, profile, enable_search)

    if action["type"] == "regen" and idx > 0:
        # Drop assistant at idx; resubmit with history up to previous user
        chat["messages"] = messages[:idx]
        api_msgs = [{"role": "system", "content": system_content}] + [
            m for m in chat["messages"] if m["role"] != "system" or m is chat["messages"][0]
        ]
        # Rebuild cleanly
        api_msgs = [{"role": "system", "content": system_content}]
        for m in chat["messages"]:
            if m["role"] != "system":
                api_msgs.append(m)
        with st.chat_message("assistant"):
            if compare_mode and model_b:
                c1, c2 = st.columns(2)
                with c1:
                    st.caption(model_option)
                    r1 = st.write_stream(stream_completion(model_option, api_msgs, temperature))
                with c2:
                    st.caption(model_b)
                    r2 = st.write_stream(stream_completion(model_b, api_msgs, temperature))
                full = f"**{model_option}:**\n{r1}\n\n---\n\n**{model_b}:**\n{r2}"
            else:
                full = st.write_stream(stream_completion(model_option, api_msgs, temperature))
            chat["messages"].append({"role": "assistant", "content": full})
            chat["updated_at"] = now_iso()
            save_chats(st.session_state.chats)

    elif action["type"] == "continue":
        api_msgs = [{"role": "system", "content": system_content}]
        for m in messages:
            if m["role"] != "system":
                api_msgs.append(m)
        api_msgs.append({"role": "user", "content": "Please continue from where you left off."})
        with st.chat_message("assistant"):
            full = st.write_stream(stream_completion(model_option, api_msgs, temperature))
            chat["messages"].append({"role": "assistant", "content": full})
            chat["updated_at"] = now_iso()
            save_chats(st.session_state.chats)

    elif action["type"] == "style":
        style = action["style"]
        original = messages[idx]["content"]
        api_msgs = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"Rewrite the following reply to be {style}. Keep the same meaning.\n\n{original}"},
        ]
        with st.chat_message("assistant"):
            full = st.write_stream(stream_completion(model_option, api_msgs, temperature))
            # Replace the message
            chat["messages"][idx] = {"role": "assistant", "content": full}
            chat["updated_at"] = now_iso()
            save_chats(st.session_state.chats)
            st.rerun()

# Voice input
audio = st.audio_input("🎤 Voice message (optional)", label_visibility="visible")
voice_text = None
if audio is not None:
    audio_bytes = audio.read()
    with st.spinner("Transcribing…"):
        voice_text = transcribe_audio(audio_bytes, getattr(audio, "name", "audio.wav"))
    if voice_text and not voice_text.startswith("[transcription"):
        st.info(f"Transcribed: {voice_text}")

# Text input
prompt = st.chat_input("What is on your mind?")
if voice_text and not voice_text.startswith("[transcription") and not prompt:
    prompt = voice_text

if prompt:
    # Optional web search
    extra_context = ""
    if enable_search and DDGS is not None:
        # Simple heuristic: search when question-like or user asks
        q = prompt.strip()
        if any(w in q.lower() for w in ["search", "look up", "what is", "who is", "latest", "news", "current"]):
            with st.spinner("Searching the web…"):
                extra_context = web_search(q)

    chat["messages"].append({"role": "user", "content": prompt})
    # Auto-title from first user message
    if chat.get("title") in ("New chat", "Untitled", "") and len([m for m in chat["messages"] if m["role"] == "user"]) == 1:
        chat["title"] = prompt[:48] + ("…" if len(prompt) > 48 else "")

    with st.chat_message("user"):
        st.markdown(prompt)
        if extra_context:
            with st.expander("Web search results used"):
                st.markdown(extra_context)

    system_content = build_system_message(preset, custom_sys, profile, enable_search)
    api_msgs = [{"role": "system", "content": system_content}]
    for m in chat["messages"]:
        if m["role"] != "system":
            api_msgs.append(m)
    if extra_context:
        api_msgs.insert(-1, {"role": "system", "content": f"[WEB SEARCH]\n{extra_context}"})

    with st.chat_message("assistant"):
        if compare_mode and model_b:
            c1, c2 = st.columns(2)
            with c1:
                st.caption(model_option)
                r1 = st.write_stream(stream_completion(model_option, api_msgs, temperature))
            with c2:
                st.caption(model_b)
                r2 = st.write_stream(stream_completion(model_b, api_msgs, temperature))
            full = f"**{model_option}:**\n{r1}\n\n---\n\n**{model_b}:**\n{r2}"
        else:
            full = st.write_stream(stream_completion(model_option, api_msgs, temperature))
        chat["messages"].append({"role": "assistant", "content": full})
        chat["updated_at"] = now_iso()
        save_chats(st.session_state.chats)

# ---------------------------------------------------------------------------
# Cluster results
# ---------------------------------------------------------------------------
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
    fig.update_layout(height=400, margin=dict(l=20, r=20, t=50, b=20),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    cols = st.columns(min(3, result["n_clusters"]))
    for i, name in enumerate(names):
        with cols[i % len(cols)]:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.caption(f"{result['sizes'][i]} message(s)")
                members = [result["texts"][j] for j in range(len(result["texts"])) if result["labels"][j] == i]
                for m in members[:3]:
                    st.markdown(f"- _{m[:120]}{'…' if len(m) > 120 else ''}_")
                if len(members) > 3:
                    st.caption(f"+ {len(members) - 3} more")
