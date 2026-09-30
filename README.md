# ideal-chainsaw 🤖

A minimalist, high-contrast **AI chat app** built with **Python**, **Streamlit**, and the official **Groq Cloud SDK**. Developed on **Debian 13 (Trixie)**.

Streams open-source LLMs in real time via Groq — no local GPU required.

## ✨ Key Features

- **Official Groq SDK** — typed streaming completions, embeddings, and Whisper transcription
- **Dynamic model list** — live catalog from Groq (with safe fallbacks)
- **Persistent named chats** — multiple conversations saved under `data/chats.json` (local)
- **Message actions** — regenerate, continue, shorter / longer / more formal, download reply
- **Context meter** — approximate token usage with optional “summarize older messages” trim
- **System presets + profile** — Helpful / Engineer / Teacher / Concise / Creative / Custom, plus a persistent “about you” snippet
- **Multi-model compare** — stream the same prompt to two models side by side
- **Web search tool** — optional DuckDuckGo search injected into context when relevant
- **Voice input** — record audio → Groq Whisper transcription → send as message
- **K-means topic clustering** — Groq `nomic-embed-text-v1_5` embeddings + scikit-learn + PCA + LLM topic labels; scope = current chat or all chats
- **Dark / light theme** — high-contrast grayscale UI
- **Export** — download the current chat as Markdown
- **Creativity control** — temperature slider

## 🛠️ Tech Stack

| Layer | Tech |
|-------|------|
| UI | Streamlit |
| LLM / embeddings / STT | Groq Python SDK |
| Clustering | scikit-learn (K-means, PCA) + Plotly |
| Web search | duckduckgo-search |
| Persistence | Local JSON (`data/`) |

## 🚀 Local setup

```bash
git clone https://github.com/Dr-Aura/ideal-chainsaw.git
cd ideal-chainsaw
python3 -m venv ai-env
source ai-env/bin/activate   # Windows: ai-env\Scripts\activate
pip install -r requirements.txt
```

Create secrets (never commit this file):

```bash
mkdir -p .streamlit
cat << 'LOCAL_EOF' > .streamlit/secrets.toml
GROQ_API_KEY = "gsk_your_actual_private_key_here"
LOCAL_EOF
```

Run:

```bash
streamlit run app.py
```

Open `http://localhost:8501/`.

Chat history and settings are stored in the local `data/` folder (gitignored).

## 🌐 Streamlit Community Cloud

1. Push this repo to GitHub.
2. Deploy on Streamlit Community Cloud.
3. Add `GROQ_API_KEY = "gsk_..."` under **Secrets** (TOML).

Note: on Community Cloud the filesystem is ephemeral, so chat persistence resets on reboot. Export chats you care about, or run locally for durable history.

## 📜 License

MIT — see [LICENSE](LICENSE).
