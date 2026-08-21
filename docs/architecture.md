# Architecture notes & how this maps to your resume

This project exists to make "RAG (Retrieval-Augmented Generation)" on your
resume defensible in an interview, and to give the Core Technical Skills
list something concrete behind it. Each piece below maps to a specific line
on your resume or a bullet from the Cigna deep-dive.

## Component-by-component

**Synthetic data generator (`data/generate_synthetic_data.py`)**
Stands in for the ingestion layer you describe at Cigna ("Built automated
data ingestion pipelines using Fivetran and AWS services"). In a real
deployment this step is Fivetran connectors + S3/Glue for anything Fivetran
doesn't cover — the generator's only job here is to produce a realistic,
legally-clean dataset to build the rest of the pipeline against.

**dbt project (`dbt_project/`)**
Directly demonstrates: "Developed modular dbt transformation models" (the
staging → intermediate → marts layering), "Designed and implemented
dimensional data models (star schema)" (`dim_members`, `dim_providers`,
`dim_date`, `fct_claims`), and SCD Type 1/2 from your Data Modeling skill
line — `dim_members` is a real SCD Type 2 dimension, and `fct_claims` does
a genuine as-of join against it so each claim reports the plan the member
had *on the date of service*, not their current plan. That distinction is a
good one to explain out loud in an interview — it's the kind of detail that
signals you've actually built this before, not just read about it.

**Data quality (`dbt_project/models/**/_*.yml`)**
22 dbt tests (not_null, unique, accepted_values, relationships) — this is
your "Implemented data validation and quality checks" bullet. Worth
mentioning: while building this, the as-of join initially produced null
`plan_type_at_service` for ~33% of claims, traced to claims being generated
with service dates before some members' plan enrollment dates. That's a real
example of exactly the kind of data quality issue this bullet is about —
happy to point an interviewer at it as a concrete story rather than a
hypothetical.

**Airflow DAG (`airflow/dags/claims_pipeline_dag.py`)**
Your "Orchestrated workflows using Apache Airflow DAGs" bullet — retries,
failure alerting, and explicit task dependencies (seed → run → test → RAG
index rebuild, with a fan-in failure-notification task). Written to run
under a real Airflow install; this repo runs the same steps locally via
`scripts/run_pipeline.sh` without requiring a scheduler.

**Hybrid retriever (`rag/`)**
This is the new piece — RAG — and the reason it's a *hybrid* retriever
rather than plain document search is deliberate: `retriever.py` detects
claim/member IDs in the question and pulls the actual row from
`fct_claims`/`dim_members` via DuckDB SQL, then merges that with vector
search over the policy documents. That combination is the strongest thing
to lead with when asked "tell me about the RAG project" — it shows you
understand RAG needs grounding in real data, not just a document corpus.

**LLM layer (`rag/llm.py`)**
Provider-switchable (Anthropic/OpenAI) via LangChain and a `.env` file —
worth mentioning you deliberately kept the embedding/generation boundary
swappable, since that's exactly the kind of abstraction a production RAG
system needs when model providers or pricing change.

**Streamlit app (`app/streamlit_app.py`)**
Your Streamlit skill line, used as the interface layer — same tool you list
from the CONA Services role.

## Anticipated interview questions

**"Why TF-IDF instead of a transformer embedding model?"**
Be straight about this one: it was a deliberate choice to keep the project
fully local and dependency-light (no model download, no API key needed just
to test retrieval), and the retriever is written so swapping in
`HuggingFaceEmbeddings` or `OpenAIEmbeddings` is a one-line change — same
interface, same FAISS index code. If pushed, you can say TF-IDF actually
performs reasonably well here *because* the corpus is small and
domain-specific (plan names, procedure codes, denial codes are exact
keyword matches) — semantic embeddings matter more at larger scale or with
more paraphrased queries.

**"How would this actually run on Snowflake instead of DuckDB?"**
Point to `dbt_project/profiles.yml`'s `prod_snowflake` target — the dbt
models don't change, only the target. The one DuckDB-specific model
(`dim_date`, which uses `generate_series`) has a comment noting its
Snowflake equivalent.

**"What's the retrieval quality/precision like?"**
Be honest that this is a demo-scale corpus (5 policy documents, 15 chunks) —
the interesting engineering is the hybrid pattern, not large-scale retrieval
tuning. If asked to extend it, the natural next step is more policy
documents plus a re-ranking step.
