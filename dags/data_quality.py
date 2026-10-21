from datetime import datetime, timedelta
from airflow.decorators import dag, task
from pipeline.quality.check_dataset import check_dataset
from pipeline.quality.publish_report import publish_report


@dag(
    dag_id="data_quality",
    description="Checks the marked table and saves the HTML report.",
    schedule="*/5 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(seconds=30)},
    tags=["mlops", "dq"],
)
def data_quality():
    checked = task(check_dataset, task_id="check_dataset")()
    task(publish_report, task_id="publish_report")(checked)


data_quality()