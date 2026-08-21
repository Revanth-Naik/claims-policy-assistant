"""
Orchestrates the full claims + RAG pipeline daily:

  1. generate/refresh source data          (stands in for the Fivetran sync
                                             landing claims/EHR/pharmacy data)
  2. dbt seed + dbt run                    (build the star schema in the
                                             warehouse -- DuckDB here, Snowflake
                                             in production via `--target prod_snowflake`)
  3. dbt test                              (data quality gate -- pipeline
                                             fails loudly instead of shipping
                                             bad data downstream)
  4. rebuild the RAG vector index          (re-embed policy docs if any changed)
  5. notify on failure                     (Slack/email hook -- stubbed here)

This mirrors the "Orchestrated workflows using Apache Airflow DAGs, ensuring
reliable pipeline execution" bullet: retries, failure alerting, and explicit
task dependencies rather than a single monolithic script.

This file is written to run under a real Airflow installation (2.7+) and is
not executed inside this repo's local demo -- there's no Airflow scheduler
bundled here on purpose, to keep the local setup lightweight. `scripts/run_pipeline.sh`
runs the equivalent steps directly for local development.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

PROJECT_ROOT = "/opt/airflow/claims-policy-assistant"  # mount point in the Airflow container

default_args = {
    "owner": "data-eng",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": True,
    "email": ["data-alerts@example.com"],
}

with DAG(
    dag_id="claims_policy_assistant_pipeline",
    description="Refresh claims star schema and RAG index for the Claims & Policy Assistant",
    default_args=default_args,
    schedule_interval="0 5 * * *",  # daily at 05:00
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["claims", "dbt", "rag"],
) as dag:

    generate_source_data = BashOperator(
        task_id="generate_source_data",
        bash_command=f"cd {PROJECT_ROOT} && python data/generate_synthetic_data.py",
    )

    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=(
            f"cd {PROJECT_ROOT}/dbt_project && "
            "DBT_PROFILES_DIR=. dbt seed --target prod_snowflake"
        ),
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f"cd {PROJECT_ROOT}/dbt_project && "
            "DBT_PROFILES_DIR=. dbt run --target prod_snowflake"
        ),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"cd {PROJECT_ROOT}/dbt_project && "
            "DBT_PROFILES_DIR=. dbt test --target prod_snowflake"
        ),
    )

    def _rebuild_rag_index(**_):
        import subprocess
        subprocess.run(["python", "rag/ingest.py"], cwd=PROJECT_ROOT, check=True)

    rebuild_rag_index = PythonOperator(
        task_id="rebuild_rag_index",
        python_callable=_rebuild_rag_index,
    )

    def _notify_failure(**context):
        # Stand-in for a real Slack/PagerDuty hook.
        print(f"Pipeline failed: {context['dag_run'].dag_id} on {context['ds']}")

    notify_on_failure = PythonOperator(
        task_id="notify_on_failure",
        python_callable=_notify_failure,
        trigger_rule=TriggerRule.ONE_FAILED,
    )

    generate_source_data >> dbt_seed >> dbt_run >> dbt_test >> rebuild_rag_index
    [dbt_seed, dbt_run, dbt_test, rebuild_rag_index] >> notify_on_failure
