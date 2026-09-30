# ideal-chainsaw 🤖

A minimalist, production-oriented **AI chat app** built with **Python**, **Streamlit**, and the official **Groq Cloud SDK**.

Streams open-source LLMs in real time via Groq — no local GPU required. Tuned for **Debian 13 (Trixie)**.

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
lib/                   # Application package
scripts/
  setup_debian.sh      # venv + pip install (works from any directory)
  run.sh               # start app (works from any directory)
Dockerfile
data/                  # Local chats/settings (gitignored)
```

## 🐧 Debian 13 / Ubuntu

System Python is **externally managed** (PEP 668). Do **not** use system `pip`, `sudo pip`, or `--break-system-packages`.

**Shell note:** Debian is case-sensitive. The directory command is lowercase `cd` (not `CD`). The setup scripts find the project root themselves — you do **not** need to change directory first.

### Setup (no `cd` required)

```bash
git clone https://github.com/Dr-Aura/ideal-chainsaw.git

# Run setup by path — works from wherever you are
bash ideal-chainsaw/scripts/setup_debian.sh
```

Or if you are already inside the repo folder:

```bash
bash scripts/setup_debian.sh
```

Recreate the venv from scratch:

```bash
bash ideal-chainsaw/scripts/setup_debian.sh --force
```

The script will:

1. Install `python3-venv` / `python3-pip` via apt if missing
2. Create `ideal-chainsaw/ai-env/`
3. Install everything from `requirements.txt` **inside the venv**
4. Create `.streamlit/secrets.toml` if missing
5. Verify imports (`streamlit`, `groq`, etc.)

### Run (no `cd` required)

```bash
bash ideal-chainsaw/scripts/run.sh
```

Put your key in `ideal-chainsaw/.streamlit/secrets.toml`:

```toml
GROQ_API_KEY = "gsk_your_real_key"
```

Or:

```bash
export GROQ_API_KEY=gsk_...
bash ideal-chainsaw/scripts/run.sh
```

Open http://localhost:8501/

### If a path fails

```bash
# Show where you are and list the repo
pwd
ls -la ideal-chainsaw/scripts/

# Use an absolute path (replace with your real home path)
bash /home/YOURUSER/ideal-chainsaw/scripts/setup_debian.sh
bash /home/YOURUSER/ideal-chainsaw/scripts/run.sh
```

## 🐳 Docker (no host Python / no venv)

```bash
docker build -t ideal-chainsaw ideal-chainsaw
docker run --rm -p 8501:8501 \
  -e GROQ_API_KEY=gsk_... \
  -v chainsaw-data:/app/data \
  ideal-chainsaw
```

## ☁️ Streamlit Community Cloud

1. Deploy this repo.
2. Secrets → `GROQ_API_KEY = "gsk_..."`
3. Disk is ephemeral — use **Export** for important chats, or Docker/local for durable storage.

## 🔒 Production notes

| Guard | Default |
|-------|---------|
| Max user message | 12 000 chars |
| Max messages / chat | 200 |
| Max stored chats | 50 |
| Groq retries | 5 |
| Groq timeout | 90s |

See [PRIVACY.md](PRIVACY.md). MIT license — [LICENSE](LICENSE).
