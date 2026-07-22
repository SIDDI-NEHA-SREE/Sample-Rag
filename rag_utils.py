"""
rag_utils.py
Core RAG engine used by app.py

Uses:
- Google Gemini (Embeddings + LLM)
- ChromaDB
- PDF / DOCX / TXT

Author: Updated for Gemini AI
"""

import os
import uuid
from pathlib import Path

import chromadb
import docx

from dotenv import load_dotenv
from google import genai
from pypdf import PdfReader

# ---------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY not found. Please add it to your .env file."
    )

# ---------------------------------------------------------------------
# Gemini Configuration
# ---------------------------------------------------------------------

client = genai.Client(api_key=GEMINI_API_KEY)

EMBED_MODEL = "gemini-embedding-001"
CHAT_MODEL = "gemini-2.5-flash-lite"

# ---------------------------------------------------------------------
# Chroma Configuration
# ---------------------------------------------------------------------

CHROMA_DIR = os.getenv("CHROMA_DIR", "chroma_db")
COLLECTION_NAME = "rag_documents"

# ---------------------------------------------------------------------
# Document Extraction
# ---------------------------------------------------------------------


def extract_text_from_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)

    pages = []

    for page in reader.pages:
        pages.append(page.extract_text() or "")

    return "\n".join(pages)


def extract_text_from_docx(file_path: str) ->str:
    document = docx.Document(file_path)

    return "\n".join(
        p.text
        for p in document.paragraphs
        if p.text.strip()
    )


def extract_text_from_txt(file_path: str) ->str:
    with open(
        file_path,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as f:
        return f.read()


def extract_text(file_path: str) ->str:

    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)

    elif ext == ".docx":
        return extract_text_from_docx(file_path)

    elif ext == ".txt":
        return extract_text_from_txt(file_path)

    raise ValueError(f"Unsupported file: {ext}")


# ---------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
):
    text = text.strip()

    if not text:
        return []

    chunks = []

    start = 0

    while start < len(text):

        end = min(start + chunk_size, len(text))

        chunks.append(text[start:end])

        if end == len(text):
            break

        start = end - overlap

    return chunks


# ---------------------------------------------------------------------
# Gemini Embeddings
# ---------------------------------------------------------------------


def embed_text(text):
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )

    return response.embeddings[0].values


# ---------------------------------------------------------------------
# ChromaDB
# ---------------------------------------------------------------------


def get_chroma_collection():

    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

    return chroma_client.get_or_create_collection(
        name=COLLECTION_NAME
    )


# ---------------------------------------------------------------------
# Index Documents
# ---------------------------------------------------------------------


def add_document_to_store(
    file_path: str,
    file_name: str,
    progress_callback=None
):

    text = extract_text(file_path)

    chunks = chunk_text(text)

    if not chunks:
        return 0

    collection = get_chroma_collection()

    ids = []
    embeddings = []
    documents = []
    metadatas = []

    total = len(chunks)

    for i, chunk in enumerate(chunks):

        embedding = embed_text(chunk)

        ids.append(
            f"{file_name}-{uuid.uuid4().hex[:8]}-{i}"
        )

        embeddings.append(embedding)

        documents.append(chunk)

        metadatas.append(
            {
                "source": file_name,
                "chunk_index": i
            }
        )

        if progress_callback:
            progress_callback(i + 1, total)

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )

    return total


# ---------------------------------------------------------------------
# Clear Database
# ---------------------------------------------------------------------


def clear_store():

    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

    try:
        chroma_client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass


# ---------------------------------------------------------------------
# Indexed Files
# ---------------------------------------------------------------------


def get_indexed_sources():

    collection = get_chroma_collection()

    data = collection.get()

    sources = set()

    for meta in data.get("metadatas", []):

        if meta and "source" in meta:
            sources.add(meta["source"])

    return sorted(sources)


# ---------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------


def retrieve_context(
    question: str,
    n_results: int = 5
):

    collection = get_chroma_collection()

    if collection.count() == 0:
        return []

    query_embedding = embed_text(question)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]

    contexts = []

    for doc, meta, dist in zip(
        docs,
        metas,
        dists
    ):

        contexts.append(
            {
                "text": doc,
                "source": meta.get(
                    "source",
                    "Unknown"
                ),
                "distance": dist,
            }
        )

    return contexts


# ---------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------


def build_prompt(
    question,
    contexts
):

    context = "\n\n-----------------\n\n".join(
        f"Source: {c['source']}\n\n{c['text']}"
        for c in contexts
    )

    return f"""
You are a helpful AI assistant.

Answer ONLY using the information provided in the context.

If the answer cannot be found in the context, reply:

"I couldn't find that information in the uploaded documents."

Context:

{context}

Question:

{question}

Provide a concise and accurate answer.

Mention the source document(s) used.
"""


# ---------------------------------------------------------------------
# Gemini Answer Generation
# ---------------------------------------------------------------------


def generate_answer(
    question,
    contexts,
    chat_history=None
):

    prompt = build_prompt(
        question,
        contexts
    )

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=prompt
    )

    return response.text
