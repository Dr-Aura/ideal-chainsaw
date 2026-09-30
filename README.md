# ideal-chainsaw 🤖

A minimalist, production-oriented **AI chat app** built with **Python**, **Streamlit**, and the official **Groq Cloud SDK**.

Streams open-source LLMs in real time via Groq — no local GPU required. Developed and tested with **Debian 13 (Trixie)** in mind.

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
app.py                 # Streamlit UI
lib/                   # Application package (config, storage, Groq, clustering, search)
scripts/
  setup_debian.sh      # Debian/Ubuntu venv setup (PEP 668 safe)
  run.sh               # Activate venv and start Streamlit
Dockerfile
data/                  # Local chats/settings (gitignored)
```

## 🐧 Debian 13 / Ubuntu (recommended)

Debian and Ubuntu mark system Python as **externally managed** (PEP 668).
Installing packages with system `pip` fails with:

```text
error: externally-managed-environment
```

**Always use a virtual environment.** Do not use `sudo pip` or `--break-system-packages`.

### One-command setup

```bash
git clone https://github.com/Dr-Aura/ideal-chainsaw.git
cd ideal-chainsaw
bash scripts/setup_debian.sh
```

The script will:

1. Install `python3-venv` / `python3-pip` via apt if missing (asks for sudo)
2. Create `ai-env/`
3. `pip install -r requirements.txt` **inside the venv only**
4. Create a template `.streamlit/secrets.toml` if none exists

### Run

```bash
bash scripts/run.sh
# or:
source ai-env/bin/activate
streamlit run app.py
```

Edit `.streamlit/secrets.toml` and set your real `GROQ_API_KEY`, or:

```bash
export GROQ_API_KEY=gsk_...
source ai-env/bin/activate
streamlit run app.py
```

### Manual steps (same result)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip

python3 -m venv ai-env
source ai-env/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

mkdir -p .streamlit
printf '%s\n' 'GROQ_API_KEY = "gsk_your_actual_private_key_here"' > .streamlit/secrets.toml

streamlit run app.py
```

Open http://localhost:8501/

## 🐳 Docker (avoids host Python entirely)

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
