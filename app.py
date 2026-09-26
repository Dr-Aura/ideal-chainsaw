import streamlit as st
import requests

st.set_page_config(page_title="AI Cloud Assistant", page_icon="🤖", layout="wide")

# The correct API endpoint base structure
GROQ_API_BASE = "https://groq.com"
FALLBACK_MODELS = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "gemma2-9b-it"]

if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    st.error("Please add your GROQ_API_KEY to the Streamlit Secrets manager.")
    st.stop()


@st.cache_data(ttl=3600)  # Refresh cache list once per hour maximum
def fetch_available_models(key: str) -> list[str]:
    """GET the current list of active model IDs from Groq."""
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
    st.title("⚙️ AI Configuration")

    available_models = fetch_available_models(api_key)

    model_option = st.selectbox(
        "Choose a model:",
        available_models,
        index=0
    )

    st.markdown("---")
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("🤖 Custom Cloud AI Assistant")
st.caption(f"Powered by Groq Cloud | Active Model: `{model_option}`")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display conversation history visually
for message in st.session_state.messages:
    # Skip rendering system rules on the screen
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
        
        # LANGUAGE RULE UPGRADE: Inject a system instruction payload to enforce English
        api_messages = [{"role": "system", "content": "You are a helpful AI assistant. You must always reply in English."}]
        api_messages.extend(st.session_state.messages)
        
        payload = {
            "model": model_option,
            "messages": api_messages
        }
        try:
            response = requests.post(
                f"{GROQ_API_BASE}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            if response.status_code != 200:
                reply = f"⚠️ API Error (Status {response.status_code}): {response.text}"
            else:
                response_json = response.json()
                reply = response_json["choices"][0]["message"]["content"]
        except Exception as e:
            reply = f"⚠️ Network Connection Error: {str(e)}"

        st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
