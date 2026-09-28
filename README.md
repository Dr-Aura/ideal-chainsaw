# Custom Cloud AI Assistant 🤖

A minimalist, high-contrast, fully responsive **AI Chat Application** built using **Python**, **Streamlit**, and the official **Groq Cloud SDK**. This project was developed and optimized natively on **Debian 13 (Trixie)**.

The application bypasses heavy local hardware constraints (like dedicated GPUs) by securely communicating with Groq's high-speed inference clusters to stream large open-source language models natively in real-time.

## ✨ Key Features
- **Official Groq SDK Integration:** Built using type-safe completion streams (`chunk.choices[0].delta.content`) for robust, crash-free data processing.
- **Dynamic Model Retrieval:** Automatically queries the live Groq engine catalog on boot to prevent broken dependencies from retired models.
- **Persistent Context Memory:** Tracks full conversational history state dynamically across user prompts.
- **Minimalist Grayscale UI:** Features a high-visibility, lightweight monochrome palette designed for maximum legibility and responsiveness across devices.
- **Creativity Control:** Features a live sidebar temperature slider to seamlessly adjust the model's tone from strict/analytical to creative/experimental.

## 🛠️ Architecture & Tech Stack
- **Frontend/Framework:** Streamlit (Responsive Viewport Mode)
- **API Engine Client:** Official Groq Python Client Library
- **Operating System Baseline:** Debian 13 Linux

## 🚀 Local Installation & Setup

If you want to run this private interface locally on your machine, follow these steps:

### 1. Clone the Repository
```bash
git clone https://github.com/Dr-Aura/ideal-chainsaw.git
cd ideal-chainsaw
```

### 2. Create and Activate a Virtual Environment
```bash
python3 -m venv ai-env
source ai-env/bin/activate
```

### 3. Install Package Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Your Private API Credentials
Create a local-only secrets configuration file (this file should be protected by `.gitignore` so it stays safe from public commits):
```bash
mkdir -p .streamlit
cat << 'LOCAL_EOF' > .streamlit/secrets.toml
GROQ_API_KEY = "gsk_your_actual_private_key_here"
LOCAL_EOF
```

### 5. Boot Up the Interface
```bash
streamlit run app.py
```
Open your web browser and navigate to `http://localhost:8501/`.

## 🌐 Cloud Deployment
This project is configured out-of-the-box for deployment on **Streamlit Community Cloud**. To deploy:
1. Push this repository to your GitHub account.
2. Link your account to Streamlit Community Cloud.
3. Inject your `GROQ_API_KEY = "gsk_..."` directly into the deployment dashboard's **Secrets** management panel under TOML notation.

## 📜 License
This project is open-source and free to adapt.
