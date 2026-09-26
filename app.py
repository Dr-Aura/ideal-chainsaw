import streamlit as st
import requests

st.title("My Cloud AI Assistant")

# Securely grab the API key from Streamlit's dashboard secrets
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    st.error("Please add your GROQ_API_KEY to the Streamlit Secrets manager.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is on your mind?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Post to Groq Cloud endpoint using an optimized Llama model
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}]
        }
        
        try:
            response = requests.post(
                "https://groq.com",
                headers=headers,
                json=payload
            )
            response_json = response.json()
            reply = response_json["choices"][0]["message"]["content"]
        except Exception as e:
            reply = "Error connecting to the AI Cloud server."

        st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
