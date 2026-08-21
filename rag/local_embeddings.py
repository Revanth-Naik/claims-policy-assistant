"""
A fully local, dependency-light embedding backend (TF-IDF over the policy
corpus) that needs no external model download and no API key -- it runs
anywhere, including network-locked environments.

For a real deployment, swap this for higher-quality semantic embeddings with
no other code changes: LangChain's `HuggingFaceEmbeddings` (sentence-
transformers, local but downloads a model) or `OpenAIEmbeddings` /
`VoyageAIEmbeddings` (API-based) all implement the same `embed_documents` /
`embed_query` interface used by `FAISS.from_documents` in ingest.py and
`FAISS.load_local` in retriever.py. In production on Snowflake, this whole
module is replaced by Snowflake Cortex Search, which handles chunking,
embedding, and indexing natively next to the warehouse data.
"""
import pickle

from langchain_core.embeddings import Embeddings
from sklearn.feature_extraction.text import TfidfVectorizer


class LocalTfidfEmbeddings(Embeddings):
    def __init__(self, max_features: int = 4000):
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),
            stop_words="english",
        )
        self._fitted = False

    def fit(self, texts: list[str]):
        self.vectorizer.fit(texts)
        self._fitted = True
        return self

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not self._fitted:
            raise RuntimeError("LocalTfidfEmbeddings must be fit() before embedding.")
        return self.vectorizer.transform(texts).toarray().tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def save(self, path: str):
        with open(path, "wb") as f:
            pickle.dump(self.vectorizer, f)

    @classmethod
    def load(cls, path: str) -> "LocalTfidfEmbeddings":
        obj = cls()
        with open(path, "rb") as f:
            obj.vectorizer = pickle.load(f)
        obj._fitted = True
        return obj
