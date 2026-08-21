"""
Chat UI for the Claims & Policy Assistant.

Run: streamlit run app/streamlit_app.py
(Run `python rag/ingest.py` at least once first to build the vector index,
 and `dbt seed && dbt run` in dbt_project/ to build the warehouse.)
"""
import os
import sys

import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAG_DIR = os.path.join(ROOT, "rag")
if RAG_DIR not in sys.path:
    sys.path.insert(0, RAG_DIR)

from llm import SYSTEM_PROMPT, build_prompt, get_llm  # noqa: E402
from retriever import HybridRetriever  # noqa: E402

st.set_page_config(page_title="Claims & Policy Assistant", page_icon="🩺", layout="centered")

st.title("🩺 Meridian Claims & Policy Assistant")
st.caption(
    "Portfolio demo · fictional health plan, fully synthetic data · "
    "hybrid RAG over plan policy documents + a dbt-built claims star schema"
)

with st.expander("Try asking about a specific claim"):
    st.markdown(
        "Claim and member IDs look like `C0000035` and `M000494`. Run this to "
        "find a real denied claim from the demo data:\n\n"
        "```sql\nselect claim_id, member_id, denial_reason_code\n"
        "from main_marts.fct_claims where claim_status = 'Denied' limit 5;\n```"
    )

if "messages" not in st.session_state:
    st.session_state.messages = []


@st.cache_resource
def _load_retriever():
    return HybridRetriever()


def _get_llm_safely():
    try:
        return get_llm(), None
    except Exception as e:  # missing/invalid API key, etc.
        return None, str(e)


try:
    retriever = _load_retriever()
except Exception as e:
    st.error(
        "Couldn't load the vector index / warehouse. Run `python rag/ingest.py` "
        f"and `dbt seed && dbt run` (from dbt_project/) first.\n\nDetails: {e}"
    )
    st.stop()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            st.caption("Sources: " + ", ".join(sorted(set(msg["sources"]))))

question = st.chat_input("Ask about a plan, a claim, or a denial...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving policy context and claim records..."):
            ctx = retriever.get_context(question)

        llm, llm_error = _get_llm_safely()

        if llm_error:
            st.warning(
                f"No LLM configured ({llm_error}). Showing raw retrieved context instead "
                "of a generated answer -- set an API key in .env to get a real response."
            )
            answer = ""
            if ctx["structured_context"]:
                answer += f"**Structured record(s):**\n\n```\n{ctx['structured_context']}\n```\n\n"
            answer += f"**Retrieved policy context:**\n\n{ctx['policy_context']}"
            st.markdown(answer)
        else:
            prompt = build_prompt(question, ctx["structured_context"], ctx["policy_context"])
            with st.spinner("Generating answer..."):
                response = llm.invoke(
                    [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
                )
            answer = response.content
            st.markdown(answer)
            st.caption("Sources: " + ", ".join(sorted(set(ctx["sources"]))))

        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "sources": ctx["sources"]}
        )
