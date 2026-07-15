# RAG Chat — PDF / Word / TXT + ChromaDB + Ollama + Streamlit

A local Retrieval-Augmented Generation (RAG) chat app. Upload PDF, DOCX, or TXT
files, they get chunked and embedded, stored in **ChromaDB**, and questions are
answered using an **Ollama** chat model grounded in the retrieved chunks. UI is
built with **Streamlit**.

## Files in this repo

```
app.py             # Streamlit UI (chat + document upload/management)
rag_utils.py       # Core RAG engine: extraction, chunking, embeddings, retrieval, generation
requirements.txt   # Python dependencies
.gitignore
README.md
```

## ⚠️ Important: Ollama needs a running server

Ollama is not a Python library that runs "inside" your app — it's a local
server process (`ollama serve`) that the app talks to over HTTP
(`http://localhost:11434` by default). This has one big implication for
deployment:

> **Streamlit Community Cloud cannot run Ollama itself** (no way to install/run
> a background system binary there). You have two supported paths:

1. **Run everything locally** (simplest, recommended for personal use) — both
   Streamlit and Ollama run on your machine.
2. **Self-host** — run Ollama + Streamlit together on your own server/VPS
   (e.g. via Docker Compose, see below), and open the Streamlit port to the
   internet yourself.
3. **Hybrid** — run Ollama on a server you control (VPS, home server, etc.)
   with its port exposed, deploy just the Streamlit app to Streamlit
   Community Cloud, and set the `OLLAMA_HOST` in the app's sidebar / secrets
   to point at that server's URL. This works because the app only needs
   outbound HTTPS access to your Ollama host.

---

## 1. Local setup (recommended first step)

### Install Ollama
Download from https://ollama.com and install it, then pull the models you'll use:

```bash
ollama pull nomic-embed-text   # embedding model
ollama pull llama3.1           # chat model (or any model you prefer, e.g. mistral, phi3)
```

Start the Ollama server (usually starts automatically after install; if not):

```bash
ollama serve
```

### Clone the repo & install Python deps

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run the app

```bash
streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`), upload your
files in the sidebar, click **Process & Index Documents**, then ask questions
in the chat box.

---

## 2. Pushing this to GitHub

```bash
git init
git add .
git commit -m "Initial commit: RAG chat app with ChromaDB + Ollama"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

(`chroma_db/` — the local vector store folder created at runtime — is already
excluded via `.gitignore` so you don't commit your indexed data.)

---

## 3. Deploying

### Option A — Streamlit Community Cloud + a remotely hosted Ollama
1. Push this repo to GitHub (above).
2. Set up Ollama on a machine with a public/reachable address (VPS, home
   server behind a reverse proxy, etc.), pull your models there, and make sure
   port 11434 (or whatever you configure) is reachable over HTTPS — ideally
   behind a reverse proxy with auth, since Ollama has no built-in auth.
3. Go to https://share.streamlit.io, connect your GitHub repo, and deploy
   `app.py`.
4. In the deployed app's sidebar, set **Ollama host** to your server's URL
   (e.g. `https://ollama.yourdomain.com`). You can also hardcode a default via
   Streamlit **Secrets** (`Settings → Secrets`) and read it with
   `st.secrets["OLLAMA_HOST"]` if you prefer not to type it each time — the
   current app reads `OLLAMA_HOST` as an env var default, so you can also set
   it under the app's "Advanced settings → Environment variables" when
   deploying.

### Option B — Full self-host with Docker Compose (Ollama + Streamlit together)
Create a `docker-compose.yml` like this in the repo root:

```yaml
version: "3.9"
services:
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

  streamlit-app:
    build: .
    ports:
      - "8501:8501"
    environment:
      - OLLAMA_HOST=http://ollama:11434
    depends_on:
      - ollama

volumes:
  ollama_data:
```

And a `Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
```

Then:

```bash
docker compose up -d
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama pull llama3.1
```

Visit `http://<your-server-ip>:8501`. Put this behind a reverse proxy
(nginx/Caddy) with HTTPS and, ideally, basic auth if exposing it publicly.

---

## Configuration reference

These can be set as environment variables (defaults shown), and most are also
editable live from the sidebar:

| Variable             | Default                      | Purpose                          |
|----------------------|-------------------------------|-----------------------------------|
| `OLLAMA_HOST`        | `http://localhost:11434`      | Ollama server URL                |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text`             | Embedding model                  |
| `OLLAMA_CHAT_MODEL`  | `llama3.1`                     | Chat/generation model            |
| `CHROMA_DIR`         | `chroma_db`                    | Local folder for the vector store|

## How it works

1. **Upload** — PDF/DOCX/TXT files are parsed into raw text (`pypdf`,
   `python-docx`).
2. **Chunk** — text is split into ~1000-character overlapping chunks so
   context isn't lost at boundaries.
3. **Embed** — each chunk is embedded via Ollama's embedding model
   (`nomic-embed-text` by default).
4. **Store** — chunks + embeddings + metadata (source file name) are stored
   in a persistent ChromaDB collection on disk.
5. **Retrieve** — on each question, the question is embedded and the most
   similar chunks are pulled from ChromaDB.
6. **Generate** — the retrieved chunks are inserted into a prompt and sent to
   an Ollama chat model, which answers grounded in that context and cites
   source file names.

## Troubleshooting

- **"Error contacting Ollama"** — confirm `ollama serve` is running and the
  host/port in the sidebar match where it's listening.
- **Model not found** — run `ollama pull <model-name>` for both the embedding
  and chat models before using the app.
- **Slow indexing** — large PDFs generate many chunks, each requiring an
  embedding call; this is normal for local models. Consider a smaller/faster
  embedding model if needed.
- **Empty/garbled PDF text** — scanned/image-only PDFs have no extractable
  text layer; you'd need OCR (not included here) before this pipeline can
  index them.
