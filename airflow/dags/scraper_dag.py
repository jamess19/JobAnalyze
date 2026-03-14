from datetime import datetime
import pendulum
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount
import os
from dotenv import load_dotenv

# Tải file .env từ thư mục gốc của Airflow
load_dotenv('/opt/airflow/.env')

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': pendulum.datetime(2023, 1, 1, tz="Asia/Ho_Chi_Minh"),
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
    
    common_docker_args = {
        'image': 'jobanalyze_scraper:latest',
        'api_version': 'auto',
        'auto_remove': 'force',
        'docker_url': 'unix://var/run/docker.sock',
        'network_mode': 'host',
        'mount_tmp_dir': False,
        'mounts': [
            Mount(source='/opt/JobAnalyze/data', target='/app/data', type='bind'),
            Mount(source='/opt/JobAnalyze/logs', target='/app/logs', type='bind'),
            Mount(source='/opt/JobAnalyze/src/config/credentials', target='/app/src/config/credentials', type='bind'),
            Mount(source='/opt/JobAnalyze/token.json', target='/app/token.json', type='bind'),
            Mount(source='/opt/JobAnalyze/proxies.txt', target='/app/proxies.txt', type='bind'),
        ],
        'environment': {
            'DATABASE_URL': os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5433/job_market"),
            'OUTPUT_FOLDER': '/app/data',
        },
    }

    run_itviec_spider = DockerOperator(
        task_id='run_itviec_spider',
        command='python -m main --spider itviec',
        **common_docker_args
    )

    run_topcv_spider = DockerOperator(
        task_id='run_topcv_spider',
        command='python -m main --spider topcv',
        **common_docker_args
    )
    
    run_linkedin_spider = DockerOperator(
        task_id='run_linkedin_spider',
        command='python -m main --spider linkedin',
        **common_docker_args
    )

    run_itviec_spider >> run_topcv_spider >> run_linkedin_spider
