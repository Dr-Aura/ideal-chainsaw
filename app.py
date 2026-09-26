import streamlit as st
from groq import Groq

st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
        .stApp {
            background-color: #f8f9fa !important;
            color: #1a1a1a !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        section[data-testid="stSidebar"] {
            background-color: #e9ecef !important;
            border-right: 1px solid #dee2e6 !important;
        }
        .block-container {
            max-width: 900px !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            width: 100% !important;
        }
        h1, h2, h3 {
            color: #111111 !important;
            font-weight: 700 !important;
        }
        .stChatMessage {
            background-color: #ffffff !important;
            border: 1px solid #dee2e6 !important;
            border-radius: 8px !important;
            padding: 1.25rem !important;
            margin-bottom: 0.75rem !important;
            color: #212529 !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
            width: 100% !important;
        }
        div[data-testid="stChatInput"] {
            background-color: #ffffff !important;
            border-top: 1px solid #dee2e6 !important;
        }
    </style>
""", unsafe_allow_html=True)

FALLBACK_MODELS = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "gemma2-9b-it"]

if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    st.error("Please add your GROQ_API_KEY to the Streamlit Secrets manager.")
    st.stop()

# The official SDK owns the correct base URL internally — there is no host
# string here to typo or revert. This is the whole point of switching to it.
client = Groq(api_key=api_key)


@st.cache_data(ttl=3600)
def fetch_available_models(_client: Groq) -> list[str]:
    """List active model IDs via the SDK. Falls back to a known-good list on any failure."""
    try:
        models = _client.models.list()
        model_ids = [m.id for m in models.data if getattr(m, "active", True)]
        return sorted(model_ids) if model_ids else FALLBACK_MODELS
    except Exception:
        return FALLBACK_MODELS


with st.sidebar:
    st.title("⚙️ Configuration")
    available_models = fetch_available_models(client)
    model_option = st.selectbox("Choose a model:", available_models, index=0)
    temperature = st.slider("Creativity Level (Temperature):", min_value=0.0, max_value=1.0, value=0.7, step=0.1)
    st.markdown("---")
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("🤖 AI Assistant")
st.caption(f"Powered by Groq Cloud | Model: {model_option} | Temp: {temperature}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is on your mind?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        api_messages = [{"role": "system", "content": "You are a helpful AI assistant. You must always reply in English."}]
        api_messages.extend(st.session_state.messages)

        def response_generator():
            try:
                stream = client.chat.completions.create(
                    model=model_option,
                    messages=api_messages,
                    temperature=temperature,
                    stream=True,
                )
                # The SDK yields typed ChatCompletionChunk objects, not raw
                # SSE strings — no manual "choices[0]" indexing to get wrong.
                for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
            except Exception as e:
                yield f"⚠️ API Error: {str(e)}"

        full_reply = st.write_stream(response_generator())
        st.session_state.messages.append({"role": "assistant", "content": full_reply})
