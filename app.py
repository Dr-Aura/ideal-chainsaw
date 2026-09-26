import streamlit as st
import requests
import json

# --- 1. PREMIUM PAGE LAYOUT SETUP ---
st.set_page_config(page_title="AI Cloud Assistant", page_icon="🤖", layout="wide")

# --- 2. CUSTOM CSS UI DESIGN INJECTION ---
st.markdown("""
    <style>
        /* Modern subtle gradient background for the entire application */
        .stApp {
            background: linear-gradient(135deg, #131722 0%, #1c2333 100%);
            color: #e2e8f0;
        }
        
        /* Glassmorphism effect styling for the sidebar navigation */
        section[data-testid="stSidebar"] {
            background-color: rgba(23, 28, 41, 0.85) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
        }
        
        /* Premium custom text rendering styles for headings */
        h1 {
            font-family: 'Inter', sans-serif;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(90deg, #38bdf8 0%, #818cf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* Cleaner chat bubble wrappers to tighten the text spacing spacing */
        .stChatMessage {
            background-color: rgba(255, 255, 255, 0.02) !important;
            border: 1px solid rgba(255, 255, 255, 0.04);
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        /* Make the text input bar sit beautifully at the bottom of the viewport */
        div[data-testid="stChatInput"] {
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            background-color: #131722;
        }
    </style>
""", unsafe_allow_html=True)

# --- 3. HARDCODED CONFIGURATION KEYS (AUDITED & SAFE) ---
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

    # Model Selector
    model_option = st.selectbox(
        "Choose a model:",
        available_models,
        index=0
    )

    # Adjustable Creativity (Temperature) Slider
    temperature = st.slider(
        "Creativity Level (Temperature):",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="Lower values are more analytical and precise. Higher values are more creative and experimental."
    )

    st.markdown("---")
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("🤖 Custom Cloud AI Assistant")
st.caption(f"Powered by Groq Cloud | Model: `{model_option}` | Temp: `{temperature}`")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display conversation history visually
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
        
        # Enforce English system rules securely
        api_messages = [{"role": "system", "content": "You are a helpful AI assistant. You must always reply in English."}]
        api_messages.extend(st.session_state.messages)
        
        payload = {
            "model": model_option,
            "messages": api_messages,
            "temperature": temperature,
            "stream": True  # Enable streaming mode data chunks
        }
        
        # Generator function to yield text chunks as they arrive from Groq
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
                        # Convert bytes to string and strip formatting spaces
                        line_str = line.decode("utf-8").strip()
                        
                        # Groq closes streams with data: [DONE]
                        if line_str == "data: [DONE]":
                            break
                        
                        if line_str.startswith("data: "):
                            try:
                                json_data = json.loads(line_str[6:])
                                # CLAUDE FIXED INDICES: Safely grab the 0th item index list object chunk
                                choices = json_data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    if "content" in delta:
                                        yield delta["content"]
                            except Exception:
                                continue
                                
            except Exception as e:
                yield f"⚠️ Network Connection Error: {str(e)}"

        # Display streaming response to user dynamically in real-time
        full_reply = st.write_stream(response_generator())
        
        # Append the finalized completed text string to persistent conversation memory
        st.session_state.messages.append({"role": "assistant", "content": full_reply})
