"""
rag_utils.py
Core RAG engine used by app.py

Handles:
  - extracting text from PDF / DOCX / TXT
  - chunking text
  - creating embeddings via Ollama
  - storing / querying vectors in ChromaDB
  - generating answers via an Ollama chat model
"""

import os
import uuid
from pathlib import Path

import chromadb
import ollama
from pypdf import PdfReader
import docx


# ---------------------------------------------------------------------------
# Configuration (can be overridden at runtime from app.py, e.g. via sidebar)
# ---------------------------------------------------------------------------
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.1")
CHROMA_DIR = os.getenv("CHROMA_DIR", "chroma_db")
COLLECTION_NAME = "rag_documents"

_client = ollama.Client(host=OLLAMA_HOST)


# ---------------------------------------------------------------------------
# Document text extraction
# ---------------------------------------------------------------------------
def extract_text_from_pdf(file_path: str) -> str:
    text_parts = []
    reader = PdfReader(file_path)
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def extract_text_from_docx(file_path: str) -> str:
    document = docx.Document(file_path)
    return "\n".join(p.text for p in document.paragraphs if p.text.strip())


def extract_text_from_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def extract_text(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    if ext == ".docx":
        return extract_text_from_docx(file_path)
    if ext == ".txt":
        return extract_text_from_txt(file_path)
    raise ValueError(f"Unsupported file type: {ext}")


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200):
    """Simple sliding-window character chunker with overlap."""
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunks.append(text[start:end])
        if end == length:
            break
        start = end - overlap  # overlap for context continuity
    return chunks


# ---------------------------------------------------------------------------
# Embeddings (via Ollama)
# ---------------------------------------------------------------------------
def embed_text(text: str):
    response = _client.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]


# ---------------------------------------------------------------------------
# ChromaDB storage
# ---------------------------------------------------------------------------
def get_chroma_collection():
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    return chroma_client.get_or_create_collection(name=COLLECTION_NAME)


def add_document_to_store(file_path: str, file_name: str, progress_callback=None) -> int:
    """Extract, chunk, embed, and store a single file. Returns number of chunks added."""
    text = extract_text(file_path)
    chunks = chunk_text(text)
    if not chunks:
        return 0

    collection = get_chroma_collection()
    ids, embeddings, metadatas, documents = [], [], [], []

    for i, chunk in enumerate(chunks):
        embeddings.append(embed_text(chunk))
        ids.append(f"{file_name}-{uuid.uuid4().hex[:8]}-{i}")
        metadatas.append({"source": file_name, "chunk_index": i})
        documents.append(chunk)
        if progress_callback:
            progress_callback(i + 1, len(chunks))

    collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
    return len(chunks)


def clear_store():
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        chroma_client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass


def get_indexed_sources():
    collection = get_chroma_collection()
    data = collection.get()
    sources = set()
    for meta in data.get("metadatas", []) or []:
        if meta and "source" in meta:
            sources.add(meta["source"])
    return sorted(sources)


# ---------------------------------------------------------------------------
# Retrieval + Generation
# ---------------------------------------------------------------------------
def retrieve_context(question: str, n_results: int = 5):
    collection = get_chroma_collection()
    if collection.count() == 0:
        return []

    q_embedding = embed_text(question)
    results = collection.query(query_embeddings=[q_embedding], n_results=n_results)

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    return [
        {"text": doc, "source": meta.get("source", "unknown"), "distance": dist}
        for doc, meta, dist in zip(docs, metas, dists)
    ]


def build_prompt(question: str, contexts) -> str:
    context_text = "\n\n---\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in contexts
    )
    return f"""You are a helpful assistant answering questions using ONLY the context below.
If the answer isn't in the context, say you don't know — do not make something up.

Context:
{context_text}

Question: {question}

Give a clear, concise answer and mention which source file(s) it came from."""


def generate_answer(question: str, contexts, chat_history=None) -> str:
    prompt = build_prompt(question, contexts)
    messages = list(chat_history) if chat_history else []
    messages.append({"role": "user", "content": prompt})
    response = _client.chat(model=CHAT_MODEL, messages=messages)
    return response["message"]["content"]


def refresh_client(host: str):
    """Recreate the Ollama client if the host is changed at runtime (e.g. from the UI)."""
    global _client, OLLAMA_HOST
    OLLAMA_HOST = host
    _client = ollama.Client(host=host)
