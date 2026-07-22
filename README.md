# 📚 Gemini RAG Chat

A Retrieval-Augmented Generation (RAG) chatbot built with **Google Gemini AI**, **ChromaDB**, and **Streamlit**.

Upload PDF, DOCX, or TXT documents, automatically index them into a vector database, and ask questions about their contents. The chatbot retrieves the most relevant information from your uploaded documents and generates accurate responses using **Google Gemini**.

---

# 🚀 Features

- 📄 Upload PDF, DOCX, and TXT documents
- 🧩 Automatic document chunking
- 🧠 Google Gemini Embeddings (`text-embedding-004`)
- 🤖 Google Gemini 2.5 Flash / Pro for answer generation
- 🔎 Semantic search using ChromaDB
- 💬 Interactive Streamlit chat interface
- 📚 Source citations for every answer
- 📂 Persistent local ChromaDB storage
- ☁️ Streamlit Cloud deployment ready
- ⚡ No Ollama installation required

---

# 📂 Project Structure

```
app.py                  # Streamlit UI
rag_utils.py            # RAG engine
requirements.txt
README.md
.gitignore
chroma_db/              # Created automatically
```

---

# 🏗 Architecture

```
                User Uploads Documents
                         │
                         ▼
              PDF / DOCX / TXT Parser
                         │
                         ▼
                 Text Chunking
                         │
                         ▼
      Gemini Embeddings (text-embedding-004)
                         │
                         ▼
                    ChromaDB
                         │
                         ▼
                  User Question
                         │
                         ▼
      Gemini Embeddings (Question)
                         │
                         ▼
            Similarity Search
                         │
                         ▼
            Retrieved Context
                         │
                         ▼
      Gemini 2.5 Flash / Gemini 2.5 Pro
                         │
                         ▼
                 Final Response
```

---

# 🛠 Requirements

- Python 3.10+
- Google Gemini API Key
- Internet Connection

---

# 📦 Installation

Clone the repository

```bash
git clone https://github.com/<your-username>/<repository-name>.git

cd <repository-name>
```

Create a virtual environment

### Windows

```bash
python -m venv venv

venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv

source venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 Gemini API Key

Create a `.env` file in the project root.

```
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
```

You can get a free API key from:

https://aistudio.google.com/app/apikey

---

# ▶ Running the Application

```bash
streamlit run app.py
```

Open

```
http://localhost:8501
```

---

# ☁ Deploying on Streamlit Cloud

Unlike Ollama, **Gemini runs entirely in the cloud**, so users do **not** need to install anything.

## Step 1

Push your repository to GitHub.

```bash
git init

git add .

git commit -m "Initial commit"

git branch -M main

git remote add origin https://github.com/<username>/<repository>.git

git push -u origin main
```

---

## Step 2

Go to

https://share.streamlit.io

Deploy your GitHub repository.

---

## Step 3

Add your Gemini API Key.

In Streamlit Cloud

```
Settings

↓

Secrets
```

Add

```toml
GEMINI_API_KEY="YOUR_API_KEY"
```

or add it as an Environment Variable.

---

# ⚙ Configuration

| Variable | Default | Description |
|------------|-------------------|------------------------------|
| GEMINI_API_KEY | Required | Google Gemini API Key |
| CHROMA_DIR | chroma_db | Chroma database directory |
| CHAT_MODEL | gemini-2.5-flash | Gemini chat model |
| EMBED_MODEL | text-embedding-004 | Embedding model |

---

# 📖 How It Works

### 1. Upload Documents

Supported formats

- PDF
- DOCX
- TXT

---

### 2. Extract Text

The application extracts text using

- pypdf
- python-docx

---

### 3. Chunk Documents

Documents are split into overlapping chunks.

Default

- Chunk Size: 1000 characters
- Overlap: 200 characters

---

### 4. Generate Embeddings

Each chunk is converted into a vector using

```
text-embedding-004
```

---

### 5. Store Embeddings

Embeddings are stored in

```
ChromaDB
```

with metadata such as

- source filename
- chunk number

---

### 6. Retrieve

When a user asks a question,

the application

- embeds the question
- searches ChromaDB
- retrieves the most relevant chunks

---

### 7. Generate Answer

Retrieved chunks are sent to

```
Gemini 2.5 Flash
```

(or Gemini 2.5 Pro)

to generate a grounded response.

Every answer includes references to the source documents.

---

# 📚 Tech Stack

| Component | Technology |
|------------|------------|
| Frontend | Streamlit |
| LLM | Google Gemini 2.5 |
| Embeddings | text-embedding-004 |
| Vector Database | ChromaDB |
| Document Parser | pypdf |
| Word Parser | python-docx |
| Language | Python |

---

# 📸 Example Workflow

```
Upload:

📄 AI_Research.pdf

↓

Index Document

↓

Ask

"What are the main contributions?"

↓

Gemini retrieves the most relevant chunks.

↓

Answer

"The paper proposes..."

↓

Source

AI_Research.pdf
```

---

# ⚠ Troubleshooting

## Invalid API Key

Verify your

```
GEMINI_API_KEY
```

is correct.

---

## No Documents Indexed

Upload documents and click

```
Process Documents
```

before asking questions.

---

## Empty PDF

Scanned PDFs contain images instead of text.

OCR is not included.

---

## Slow Responses

Large documents generate many chunks.

This is expected.

---

# 🔮 Future Improvements

- OCR support
- Image understanding
- Excel & CSV support
- PowerPoint support
- Streaming responses
- Hybrid search (Keyword + Vector)
- Conversation memory
- Authentication
- Multi-user support
- Cloud vector databases (Pinecone, Weaviate, PGVector)

---

# 👨‍💻 Built With

- Google Gemini AI
- Streamlit
- ChromaDB
- Python

---

# 📄 License

This project is licensed under the MIT License.
