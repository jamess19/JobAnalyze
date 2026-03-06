from datetime import datetime
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
}

with DAG(
    'daily_job_scraper',
    default_args=default_args,
    description='Run job spiders daily',
    schedule_interval='0 0 * * *',
    catchup=False,
    max_active_runs=1,
) as dag:
    
    run_all_job_spiders = DockerOperator(
        task_id='run_all_job_spiders',
        image='jobanalyze_scraper:latest',
        api_version='auto',
        auto_remove='force',
        command='python -m main --spider all',
        docker_url='unix://var/run/docker.sock',
        network_mode='host',
        mounts=[
            Mount(source='/opt/JobAnalyze/src/data', target='/app/src/data', type='bind'),
            Mount(source='/opt/JobAnalyze/logs', target='/app/logs', type='bind')
        ],
        environment={
            'DATABASE_URL': '{{ var.value.get("DATABASE_URL", "postgresql://postgres:password@localhost:5433/job_market") }}'
        },
        env_file='/opt/airflow/.env',
    )

    run_all_job_spiders
