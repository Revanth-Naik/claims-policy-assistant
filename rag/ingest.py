"""
Chunks the policy documents in data/policy_docs/, embeds them locally with a
sentence-transformers model (no API key required for this half of the
pipeline), and persists a FAISS index to rag/vectorstore/.

In production this same interface swaps to Snowflake Cortex Search or a
managed vector DB (Pinecone, etc.) -- the retriever in retriever.py is the
only file that would need to change.

Run: python rag/ingest.py
"""
import os

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import FAISS

from local_embeddings import LocalTfidfEmbeddings

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(HERE, "..", "data", "policy_docs")
INDEX_DIR = os.path.join(HERE, "vectorstore")
EMBEDDER_PATH = os.path.join(INDEX_DIR, "tfidf_embedder.pkl")


def build_index():
    loader = DirectoryLoader(DOCS_DIR, glob="**/*.md", loader_cls=TextLoader)
    raw_docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(raw_docs)

    for c in chunks:
        c.metadata["source"] = os.path.basename(c.metadata.get("source", "unknown"))

    print(f"Loaded {len(raw_docs)} documents -> {len(chunks)} chunks")

    embeddings = LocalTfidfEmbeddings().fit([c.page_content for c in chunks])
    index = FAISS.from_documents(chunks, embeddings)

    os.makedirs(INDEX_DIR, exist_ok=True)
    index.save_local(INDEX_DIR)
    embeddings.save(EMBEDDER_PATH)
    print(f"Saved FAISS index -> {INDEX_DIR}")
    print(f"Saved fitted embedder -> {EMBEDDER_PATH}")
    return index


if __name__ == "__main__":
    build_index()
