"""
Hybrid retriever: combines (1) vector search over the unstructured policy
documents with (2) a structured SQL lookup against the dbt-built star schema
in DuckDB, when the question references a specific claim or member.

This is the piece that makes the project more than a "chat with your PDFs"
demo -- "why was claim C0001234 denied" needs both the specific claim record
(structured) and the plan's denial/appeals policy (unstructured) to answer
well.
"""
import os
import re
import sys

import duckdb
from langchain_community.vectorstores import FAISS

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from local_embeddings import LocalTfidfEmbeddings  # noqa: E402

INDEX_DIR = os.path.join(HERE, "vectorstore")
EMBEDDER_PATH = os.path.join(INDEX_DIR, "tfidf_embedder.pkl")
WAREHOUSE_PATH = os.path.join(HERE, "..", "warehouse.duckdb")

CLAIM_ID_RE = re.compile(r"\bC\d{7}\b")
MEMBER_ID_RE = re.compile(r"\bM\d{6}\b")


class HybridRetriever:
    def __init__(self, index_dir: str = INDEX_DIR, warehouse_path: str = WAREHOUSE_PATH):
        embeddings = LocalTfidfEmbeddings.load(os.path.join(index_dir, "tfidf_embedder.pkl"))
        self.vectorstore = FAISS.load_local(
            index_dir, embeddings, allow_dangerous_deserialization=True
        )
        self.warehouse_path = warehouse_path

    # ---- unstructured half -------------------------------------------------
    def vector_search(self, query: str, k: int = 4):
        return self.vectorstore.similarity_search(query, k=k)

    # ---- structured half ----------------------------------------------------
    def structured_lookup(self, query: str) -> str | None:
        claim_ids = CLAIM_ID_RE.findall(query)
        member_ids = MEMBER_ID_RE.findall(query)
        if not claim_ids and not member_ids:
            return None

        con = duckdb.connect(self.warehouse_path, read_only=True)
        rows_text = []
        try:
            if claim_ids:
                df = con.execute(
                    """
                    select claim_id, member_id, plan_type_at_service, provider_id,
                           specialty, network_status, service_date, procedure_code,
                           procedure_desc, billed_amount, allowed_amount, paid_amount,
                           claim_status, denial_reason_code, denial_reason_desc
                    from main_marts.fct_claims
                    where claim_id in ({placeholders})
                    """.format(placeholders=",".join(["?"] * len(claim_ids))),
                    claim_ids,
                ).fetchdf()
                for _, r in df.iterrows():
                    rows_text.append("Claim record: " + ", ".join(f"{k}={v}" for k, v in r.items()))

            if member_ids:
                df = con.execute(
                    """
                    select member_id, plan_type, region, valid_from, valid_to, is_current
                    from main_marts.dim_members
                    where member_id in ({placeholders})
                    order by valid_from
                    """.format(placeholders=",".join(["?"] * len(member_ids))),
                    member_ids,
                ).fetchdf()
                for _, r in df.iterrows():
                    rows_text.append("Member plan history record: " + ", ".join(f"{k}={v}" for k, v in r.items()))
        finally:
            con.close()

        return "\n".join(rows_text) if rows_text else None

    # ---- combined -------------------------------------------------------
    def get_context(self, query: str, k: int = 4) -> dict:
        policy_chunks = self.vector_search(query, k=k)
        structured = self.structured_lookup(query)

        policy_text = "\n\n".join(
            f"[{c.metadata.get('source', 'policy_doc')}]\n{c.page_content}" for c in policy_chunks
        )

        return {
            "policy_context": policy_text,
            "structured_context": structured,
            "sources": [c.metadata.get("source", "policy_doc") for c in policy_chunks],
        }
