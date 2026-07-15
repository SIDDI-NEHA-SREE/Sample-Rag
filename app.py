"""
app.py
Streamlit RAG chat app — PDF / DOCX / TXT documents, ChromaDB for retrieval,
Ollama for embeddings + chat generation.
"""

import os
import tempfile

import streamlit as st

import rag_utils as rag

st.set_page_config(page_title="RAG Chat — Ollama + ChromaDB", page_icon="📚", layout="wide")

st.title("📚 RAG Chat")
st.caption("Upload PDF / Word / TXT files and chat with them. Powered by ChromaDB + Ollama.")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of {"role", "content", "sources"}

# ---------------------------------------------------------------------------
# Sidebar — settings + document management
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")

    ollama_host = st.text_input(
        "Ollama host",
        value=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        help="URL where your Ollama server is running (local or remote).",
    )
    embed_model = st.text_input("Embedding model", value=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"))
    chat_model = st.text_input("Chat model", value=os.getenv("OLLAMA_CHAT_MODEL", "llama3.1"))
    n_results = st.slider("Chunks to retrieve per question", 1, 10, 5)

    # push any changed settings into rag_utils
    if ollama_host != rag.OLLAMA_HOST:
        rag.refresh_client(ollama_host)
    rag.EMBED_MODEL = embed_model
    rag.CHAT_MODEL = chat_model

    st.divider()
    st.header("📄 Documents")

    uploaded_files = st.file_uploader(
        "Upload PDF / DOCX / TXT files",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
    )

    if st.button("Process & Index Documents", use_container_width=True, disabled=not uploaded_files):
        progress_bar = st.progress(0, text="Starting...")
        total = len(uploaded_files)
        for idx, uploaded_file in enumerate(uploaded_files):
            suffix = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getbuffer())
                tmp_path = tmp.name
            try:
                progress_bar.progress(idx / total, text=f"Indexing {uploaded_file.name}...")
                n_chunks = rag.add_document_to_store(tmp_path, uploaded_file.name)
                st.success(f"Indexed **{uploaded_file.name}** ({n_chunks} chunks)")
            except Exception as e:
                st.error(f"Failed on {uploaded_file.name}: {e}")
            finally:
                os.remove(tmp_path)
        progress_bar.progress(1.0, text="Done!")

    st.divider()
    indexed_sources = rag.get_indexed_sources()
    st.subheader(f"Indexed files ({len(indexed_sources)})")
    for s in indexed_sources:
        st.write(f"• {s}")

    if st.button("🗑️ Clear all indexed documents", use_container_width=True):
        rag.clear_store()
        st.session_state.chat_history = []
        st.rerun()

# ---------------------------------------------------------------------------
# Main — chat interface
# ---------------------------------------------------------------------------
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("Sources"):
                for s in msg["sources"]:
                    st.markdown(f"**{s['source']}**  (distance: {s['distance']:.3f})")
                    preview = s["text"][:500] + ("..." if len(s["text"]) > 500 else "")
                    st.text(preview)

question = st.chat_input("Ask a question about your documents...")

if question:
    st.session_state.chat_history.append({"role": "user", "content": question, "sources": None})
    with st.chat_message("user"):
        st.markdown(question)

    contexts = []
    answer = ""

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                contexts = rag.retrieve_context(question, n_results=n_results)
                if not contexts:
                    answer = "I don't have any indexed documents yet. Please upload and process files first."
                else:
                    history_for_model = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.chat_history[:-1]
                        if m["role"] in ("user", "assistant")
                    ][-6:]
                    answer = rag.generate_answer(question, contexts, chat_history=history_for_model)
            except Exception as e:
                answer = (
                    f"⚠️ Error contacting Ollama at `{rag.OLLAMA_HOST}`: {e}\n\n"
                    "Make sure Ollama is running and reachable, and that the model "
                    "names in the sidebar are pulled (`ollama pull <model>`)."
                )

        st.markdown(answer)
        if contexts:
            with st.expander("Sources"):
                for c in contexts:
                    st.markdown(f"**{c['source']}**  (distance: {c['distance']:.3f})")
                    preview = c["text"][:500] + ("..." if len(c["text"]) > 500 else "")
                    st.text(preview)

    st.session_state.chat_history.append({"role": "assistant", "content": answer, "sources": contexts})
