# ideal-chainsaw 🤖

A minimalist, production-oriented **AI chat app** built with **Python**, **Streamlit**, and the official **Groq Cloud SDK**.

Streams open-source LLMs in real time via Groq — no local GPU required.

## ✨ Features

- **Groq SDK** — chat streaming, embeddings (`nomic-embed-text-v1_5`), Whisper STT
- **Dynamic model catalog** with safe fallbacks
- **Persistent named chats** (`data/chats.json`, atomic writes)
- **Message actions** — regenerate, continue, shorter / longer / formal, download
- **Context meter** + optional summarize-to-trim
- **System presets + user profile**
- **Multi-model compare**
- **Optional web search** (DuckDuckGo)
- **Voice input** (browser record → Whisper)
- **K-means topic clustering** (current chat or all chats)
- **Dark / light theme**, Markdown export

## 🏗️ Project layout

```
app.py              # Streamlit UI
lib/
  config.py         # Limits, presets, API key resolution
  storage.py        # Atomic JSON persistence
  groq_ops.py       # Client, retries, streaming, embeddings, STT
  clustering.py     # K-means + topic labels
  search.py         # DuckDuckGo helper
Dockerfile          # Non-root image + healthcheck
data/               # Local chats/settings (gitignored)
```

## 🚀 Local setup

```bash
git clone https://github.com/Dr-Aura/ideal-chainsaw.git
cd ideal-chainsaw
python3 -m venv ai-env
source ai-env/bin/activate
pip install -r requirements.txt

mkdir -p .streamlit
cat << 'EOF' > .streamlit/secrets.toml
GROQ_API_KEY = "gsk_your_actual_private_key_here"
EOF

streamlit run app.py
```

Or with an environment variable instead of secrets:

```bash
export GROQ_API_KEY=gsk_...
streamlit run app.py
```

## 🐳 Docker

```bash
docker build -t ideal-chainsaw .
docker run --rm -p 8501:8501 \
  -e GROQ_API_KEY=gsk_... \
  -v chainsaw-data:/app/data \
  ideal-chainsaw
```

Health endpoint: `http://localhost:8501/_stcore/health`

## ☁️ Streamlit Community Cloud

1. Deploy this repo.
2. Secrets → `GROQ_API_KEY = "gsk_..."`
3. Filesystem is **ephemeral** — chats reset on reboot. Use **Export** for anything important, or run Docker/local for durable storage.

## 🔒 Production notes

| Guard | Default |
|-------|---------|
| Max user message | 12 000 chars (`CHAINSAW_MAX_MSG_CHARS`) |
| Max messages / chat | 200 (`CHAINSAW_MAX_MESSAGES`) |
| Max stored chats | 50 (`CHAINSAW_MAX_CHATS`) |
| Groq retries | 5 (`CHAINSAW_GROQ_RETRIES`) |
| Groq timeout | 90s (`CHAINSAW_GROQ_TIMEOUT`) |
| Token warn / hard | 6 000 / 10 000 |

- API key from Streamlit secrets **or** `GROQ_API_KEY` env (never committed).
- Groq client uses official SDK retries for 429 / 5xx / connection errors.
- User-facing errors are sanitized; details go to stderr logs.
- Chat JSON is written atomically (temp file + replace).
- Non-root Docker user (`uid 10001`).
- See [PRIVACY.md](PRIVACY.md) for data handling.

## 📜 License

MIT — see [LICENSE](LICENSE).
