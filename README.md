# Claims & Policy Assistant

A hybrid RAG project: a member/provider-facing assistant that answers claims and
benefits questions by combining **vector search over plan policy documents**
with **structured SQL lookups against a dbt-built claims star schema** — so
"why was claim C0000035 denied, and how do I appeal it?" gets answered from
the *actual claim record* plus the *actual appeals policy*, not just a
generic document search.

Built as a portfolio project pairing a real data-engineering pipeline
(Snowflake/dbt/Airflow-style stack, run locally on DuckDB) with a GenAI/RAG
layer. All data is **fully synthetic** — a fictional health plan ("Meridian
Health Plan"), fictional members, fictional claims. Nothing here is real
Cigna data, and no real employer's proprietary information was used.

## Why this design

Most RAG portfolio projects are "chat with a PDF" — interesting for maybe one
interview question. This one is closer to what a real claims platform needs:
a question like a denial reason requires both an unstructured policy
explanation *and* the specific structured record, and getting that right
requires an actual data model underneath, not just a document index.

## Architecture

```
Synthetic data generator          Policy documents (.md)
        |                                 |
        v                                 v
  dbt seed (CSV -> warehouse)      rag/ingest.py
        |                          (chunk + embed -> FAISS index)
        v                                 |
  dbt run (staging -> intermediate        |
           -> marts / star schema)        |
        |                                 |
        v                                 v
  DuckDB warehouse.duckdb  <----  rag/retriever.py (hybrid retriever)
   (dim_members [SCD2], dim_providers,      |
    dim_date, fct_claims)                   v
                                     rag/llm.py (Anthropic/OpenAI)
                                            |
                                            v
                                  app/streamlit_app.py (chat UI)
```

Orchestration is modeled two ways:
- `scripts/run_pipeline.sh` — runs the whole thing locally, no scheduler needed.
- `airflow/dags/claims_pipeline_dag.py` — the same steps as a real Airflow DAG
  (retries, failure alerting, task dependencies), written to run against a
  real Airflow install; not executed by this repo directly.

## Stack

| Layer | Tool |
|---|---|
| Ingestion | Synthetic-data generator standing in for Fivetran/API/flat-file sources |
| Warehouse | DuckDB locally (file-based, zero setup) — `dbt_project/profiles.yml` includes a ready `prod_snowflake` target |
| Transformation | dbt (staging → intermediate → marts, dimensional star schema, SCD Type 2 on members) |
| Orchestration | Apache Airflow DAG (documented) + a local shell equivalent |
| Retrieval | Hybrid: FAISS vector search over policy docs + DuckDB SQL lookups on claim/member IDs mentioned in the question |
| Embeddings | Local TF-IDF (`rag/local_embeddings.py`) — zero API key, zero download, runs anywhere; swap in `HuggingFaceEmbeddings` or `OpenAIEmbeddings` for higher-quality semantic search in one line |
| Generation | LangChain, switchable between Anthropic, OpenAI, xAI (Grok), and Groq via `.env` |
| Interface | Streamlit chat app |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set LLM_PROVIDER and the matching API key
```

## Run everything

```bash
bash scripts/run_pipeline.sh      # generates data, builds the warehouse, builds the RAG index
streamlit run app/streamlit_app.py
```

## Deploy to Streamlit Community Cloud

The warehouse (`warehouse.duckdb`) and vector index (`rag/vectorstore/`) are
committed to the repo as a prebuilt demo snapshot specifically so this works
without a build step -- Streamlit Community Cloud only runs `pip install`,
it can't run `dbt run` or `rag/ingest.py` for you.

1. Push this repo to GitHub (already done if you're reading this from
   `github.com/.../claims-policy-assistant`).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** →
   pick this repo/branch, and set the main file path to:
   ```
   app/streamlit_app.py
   ```
3. Before deploying, open **Advanced settings → Secrets** and paste (TOML
   format -- pick one provider block, matching `.env.example`):
   ```toml
   LLM_PROVIDER = "groq"
   GROQ_API_KEY = "your-real-key-here"
   GROQ_MODEL = "openai/gpt-oss-120b"
   ```
4. Deploy. `app/streamlit_app.py` bridges `st.secrets` into environment
   variables at startup, so `rag/llm.py` picks them up exactly the way it
   does locally from `.env` -- no code differs between local and deployed.

To refresh the deployed data later: regenerate locally with
`bash scripts/run_pipeline.sh`, commit the updated `warehouse.duckdb` and
`rag/vectorstore/` files, and push -- Streamlit Cloud redeploys automatically
on push to the connected branch.

Without an API key set, the app still runs — it shows the retrieved
structured record + policy excerpts directly instead of a generated answer,
so you can verify retrieval quality independent of the LLM.

## Try it

Find a real denied claim from the generated data:

```bash
source .venv/bin/activate
python3 -c "
import duckdb
con = duckdb.connect('warehouse.duckdb', read_only=True)
print(con.execute(\"select claim_id, member_id, denial_reason_code from main_marts.fct_claims where claim_status='Denied' limit 5\").fetchdf())
"
```

Then ask the app things like:
- "Why was claim C0000035 denied, and how do I appeal it?"
- "Does the Gold PPO plan require prior authorization for an MRI?"
- "What's the difference in out-of-pocket max between Silver PPO and Platinum HMO?"
- "What plan was member M000494 on when they were treated?"

## Repo layout

```
data/                   synthetic data generator + generated CSVs + policy docs (.md)
dbt_project/             dbt models: staging/, intermediate/, marts/ (star schema), seeds/, tests
airflow/dags/            documented Airflow DAG
rag/                     ingest.py, retriever.py (hybrid), llm.py, local_embeddings.py
app/                     Streamlit chat UI
scripts/run_pipeline.sh  one-command local pipeline run
docs/architecture.md     component-by-component notes and interview talking points
```

## Swapping in production infrastructure

- **Warehouse**: change `target: dev` to `target: prod_snowflake` in
  `dbt_project/profiles.yml` and export the `SNOWFLAKE_*` env vars — every
  model runs unchanged (one DuckDB-specific model, `dim_date`, is commented
  with its Snowflake equivalent).
- **Vector search**: swap `LocalTfidfEmbeddings` for Snowflake Cortex Search
  and the retrieval stays entirely inside the warehouse — no separate vector
  DB to run.
- **Ingestion**: replace the synthetic-data step with real Fivetran
  connectors + S3/Glue for anything Fivetran doesn't cover natively.
