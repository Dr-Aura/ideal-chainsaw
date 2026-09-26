import streamlit as st
import requests
import json

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

# Groq's real API host is api.groq.com (with the /openai/v1 prefix), not groq.com.
# groq.com is the marketing site and will always 404/405 on API calls. Do not change this.
GROQ_API_BASE = "https://api.groq.com/openai/v1"
FALLBACK_MODELS = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "gemma2-9b-it"]

if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
    st.error("Please add your GROQ_API_KEY to the Streamlit Secrets manager.")
    st.stop()


@st.cache_data(ttl=3600)
def fetch_available_models(key: str) -> list[str]:
    headers = {"Authorization": f"Bearer {key}"}
    try:
        resp = requests.get(f"{GROQ_API_BASE}/models", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        model_ids = [m["id"] for m in data if m.get("active", True)]
        return sorted(model_ids) if model_ids else FALLBACK_MODELS
    except Exception:
        return FALLBACK_MODELS


with st.sidebar:
    st.title("⚙️ Configuration")
    available_models = fetch_available_models(api_key)
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
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        api_messages = [{"role": "system", "content": "You are a helpful AI assistant. You must always reply in English."}]
        api_messages.extend(st.session_state.messages)

        payload = {
            "model": model_option,
            "messages": api_messages,
            "temperature": temperature,
            "stream": True
        }

        def response_generator():
            try:
                response = requests.post(
                    f"{GROQ_API_BASE}/chat/completions",
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=30
                )
                if response.status_code != 200:
                    yield f"⚠️ API Error (Status {response.status_code}): {response.text}"
                    return

                for line in response.iter_lines():
                    if line:
                        line_str = line.decode("utf-8").strip()
                        if line_str == "data: [DONE]":
                            break
                        if line_str.startswith("data: "):
                            try:
                                json_data = json.loads(line_str[6:])
                                choices = json_data.get("choices", [])
                                if not choices:
                                    continue
                                # choices is a LIST — always index [0] before calling .get()
                                delta = choices[0].get("delta", {})
                                if "content" in delta and delta["content"]:
                                    yield delta["content"]
                            except Exception:
                                continue
            except Exception as e:
                yield f"⚠️ Network Connection Error: {str(e)}"

        full_reply = st.write_stream(response_generator())
        st.session_state.messages.append({"role": "assistant", "content": full_reply})
