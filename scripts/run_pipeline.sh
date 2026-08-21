#!/usr/bin/env bash
# Runs the full local pipeline: synthetic data -> dbt seed/run/test -> RAG index.
# This is the local-dev equivalent of what airflow/dags/claims_pipeline_dag.py
# runs on a schedule in a real Airflow deployment.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "==> 1/4  Generating synthetic source data"
python data/generate_synthetic_data.py
cp data/raw/*.csv dbt_project/seeds/

echo "==> 2/4  dbt seed + run + test (DuckDB, local)"
export DBT_PROFILES_DIR="$ROOT_DIR/dbt_project"
(cd dbt_project && dbt seed --full-refresh && dbt run && dbt test)

echo "==> 3/4  Rebuilding RAG vector index"
python rag/ingest.py

echo "==> 4/4  Done. Launch the app with:"
echo "        streamlit run app/streamlit_app.py"
