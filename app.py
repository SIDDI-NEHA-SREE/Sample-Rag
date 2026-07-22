
import os
import tempfile
import streamlit as st
import rag_utils as rag

st.set_page_config(page_title="Gemini RAG Chat", page_icon="📚", layout="wide")

st.markdown("""
<style>

.block-container{
    max-width:1250px;
    padding-top:1rem;
}

div[data-testid="stMetric"]{
    border-radius:14px;
    padding:15px;
    border:1px solid rgba(128,128,128,.25);
    box-shadow:0 2px 8px rgba(0,0,0,.05);
}

.stButton>button{
    border-radius:10px;
    height:45px;
    font-weight:600;
}

.stChatMessage{
    border-radius:15px;
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
# 📚 Gemini RAG Assistant

### Chat with your documents using Google's Gemini AI

Upload PDFs, Word files, or text files and get accurate answers powered by Retrieval-Augmented Generation (RAG).
""")

if "chat_history" not in st.session_state:
    st.session_state.chat_history=[]

with st.sidebar:
    st.header("⚙ Settings")
    rag.CHAT_MODEL=st.selectbox(
        "Gemini Model",
        ["gemini-2.5-flash","gemini-2.5-pro"],
        index=0
    )
    n_results=st.slider("Retrieved Chunks",1,10,5)

    st.divider()
    st.header("📄 Documents")

    uploaded=st.file_uploader(
        "Upload files",
        type=["pdf","docx","txt"],
        accept_multiple_files=True
    )

    if st.button("🚀 Process Documents", use_container_width=True, disabled=not uploaded):
        progress=st.progress(0)
        total=len(uploaded)
        for i,file in enumerate(uploaded):
            suffix=os.path.splitext(file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False,suffix=suffix) as tmp:
                tmp.write(file.getbuffer())
                path=tmp.name
            try:
                rag.add_document_to_store(path,file.name)
            finally:
                os.remove(path)
            progress.progress((i+1)/total,text=f"Indexed {file.name}")
        st.success("Indexing completed.")

    st.divider()
    files=rag.get_indexed_sources()
    st.subheader(f"Indexed Files ({len(files)})")
    for f in files:
        st.markdown(f"""
<div style="
padding:10px;
border-radius:10px;
border:1px solid #ddd;
margin-bottom:8px;">
📄 <b>{f}</b>
</div>
""", unsafe_allow_html=True)

    if st.button("🗑 Clear Knowledge Base", use_container_width=True):
        rag.clear_store()
        st.session_state.chat_history=[]
        st.rerun()

docs = len(rag.get_indexed_sources())

try:
    chunks = rag.get_chroma_collection().count()
except:
    chunks = 0

col1,col2,col3,col4 = st.columns(4)

col1.metric("📄 Documents", docs)
col2.metric("🧩 Chunks", chunks)
col3.metric("🤖 Model", rag.CHAT_MODEL)
col4.metric("✅ Status", "Ready")

st.metric("Stored Chunks",0)

st.divider()

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("📄 Sources"):
                for s in msg["sources"]:
                    st.markdown(f"**{s['source']}**")
                    st.caption(f"Distance: {s['distance']:.4f}")
                    st.write(s["text"][:600]+"..." if len(s["text"])>600 else s["text"])
if not rag.get_indexed_sources():
    st.info("""
👋 Welcome!

Upload one or more documents from the sidebar.

Then click **Process Documents**.

After indexing finishes, start asking questions.
""")

st.markdown("### 💡 Try asking")

c1,c2,c3 = st.columns(3)

if c1.button("📄 Summarize"):
    question = "Summarize the uploaded documents."

if c2.button("📌 Main Topics"):
    question = "What are the main topics?"

if c3.button("📅 Important Dates"):
    question = "List all important dates."

question=st.chat_input("Ask something about your documents...")

if question:
    st.session_state.chat_history.append({"role":"user","content":question})

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            contexts=rag.retrieve_context(question,n_results=n_results)
            if not contexts:
                answer="Please upload and index documents first."
            else:
                try:
                    answer=rag.generate_answer(question,contexts)
                except Exception as e:
                    answer=f"Error: {e}"

        st.markdown(answer)

        if contexts:
            with st.expander("📄 Sources Used"):
                for c in contexts:
                    st.markdown(f"**{c['source']}**")
                    st.caption(f"Distance: {c['distance']:.4f}")
                    st.code(
                        c["text"][:700],
                        language="text"
                    )

    st.session_state.chat_history.append({
        "role":"assistant",
        "content":answer,
        "sources":contexts if contexts else None
    })
