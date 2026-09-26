import streamlit as st
import requests

# Set page title and layout
st.set_page_config(page_title="AI Cloud Assistant", page_icon="🤖", layout="wide")

# Securely grab the API key from Streamlit's dashboard secrets
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    st.error("Please add your GROQ_API_KEY to the Streamlit Secrets manager.")
    st.stop()

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.title("⚙️ AI Configuration")
    st.markdown("Customize your open-source assistant experience.")
    
    # Model Selector
    model_option = st.selectbox(
        "Choose an open-source model:",
        (
            "llama-3.3-70b-versatile", 
            "llama-3.1-8b-instant", 
            "mixtral-8x7b-32768", 
            "gemma2-9b-it"
        ),
        index=0,
        help="Llama-3.3-70b is smartest, while Llama-3.1-8b is ultra-fast."
    )
    
    st.markdown("---")
    
    # Clear Chat Button
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- MAIN INTERFACE ---
st.title("🤖 Custom Cloud AI Assistant")
st.caption(f"Powered by Groq Cloud | Active Model: `{model_option}`")

# Initialize persistent memory structure
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display conversation history visually
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle user input
if prompt := st.chat_input("What is on your mind?"):
    # Append the user message to the conversational history memory
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # SYSTEM MEMORY UPGRADE: 
        # Instead of just sending the last prompt, we send the entire chat history context array!
        payload = {
            "model": model_option,
            "messages": st.session_state.messages
        }
        
        try:
            response = requests.post(
                "https://groq.com",
                headers=headers,
                json=payload
            )
            response_json = response.json()
            reply = response_json["choices"]["message"]["content"]
        except Exception as e:
            reply = "⚠️ Error connecting to the AI Cloud server. Please check your token or limits."

        st.markdown(reply)
        # Append assistant's reply to memory so the AI remembers it for the next question
        st.session_state.messages.append({"role": "assistant", "content": reply})
