import streamlit as st
import requests
import json

# --- 1. FULLY RESPONSIVE PAGE SETUP ---
st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")

# --- 2. CLEAN HIGH-CONTRAST GRAYSCALE VISUAL THEME ---
st.markdown("""
    <style>
        /* Light Grayscale Base Theme for Maximum Text Readability */
        .stApp {
            background-color: #f8f9fa !important;
            color: #1a1a1a !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        
        /* High-Contrast Left Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #e9ecef !important;
            border-right: 1px solid #dee2e6 !important;
        }
        
        /* Fully Fluid Responsive Content Tunnel */
        .block-container {
            max-width: 900px !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            width: 100% !important;
        }
        
        /* Crisp, Deep Charcoal Header Typography */
        h1, h2, h3 {
            color: #111111 !important;
            font-weight: 700 !important;
        }
        
        /* High-Visibility Chat Bubble Boxes */
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
        
        /* Persistent Input Bar Alignment Layer */
        div[data-testid="stChatInput"] {
            background-color: #ffffff !important;
            border-top: 1px solid #dee2e6 !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 3. AUDITED API PLATFORM CONFIGURATION ---
GROQ_API_BASE = "https://groq.com"
FALLBACK_MODELS = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "gemma2-9b-it"]

# FIXED LOGIC: Halt only if the key is missing from secrets
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
    st.title("⚙️ Configuration")

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
        step=0.1
    )

    st.markdown("---")
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("🤖 AI Assistant")
st.caption(f"Powered by Groq Cloud | Model: {model_option} | Temp: {temperature}")

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
                    stream=True,  # Crucial for handling raw byte streams
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
                                choices = json_data.get("choices", [])
                                if not choices:
                                    continue
                                
                                # FIXED INDICES IMMUTABLY: Explicitly using choices[0] array selector
                                delta = choices[0].get("delta", {})
                                if "content" in delta and delta["content"]:
                                    yield delta["content"]
                            except Exception:
                                continue
                                
            except Exception as e:
                yield f"⚠️ Network Connection Error: {str(e)}"

        # Display streaming response to user dynamically in real-time
        full_reply = st.write_stream(response_generator())
        
        # Append the finalized completed text string to persistent conversation memory
        st.session_state.messages.append({"role": "assistant", "content": full_reply})
