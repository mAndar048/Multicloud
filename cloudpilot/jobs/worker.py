"""Celery worker configuration."""

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

app = Celery(
    "cloudpilot",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["cloudpilot.jobs.tasks"],
)

# Configure connection timeouts and retry settings
app.conf.update(
    broker_connection_retry_on_startup=False,
    broker_connection_retry=True,
    broker_connection_max_retries=0,
    task_track_started=True,
    task_send_sent_event=True,
    worker_send_task_events=True,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    broker_connection_timeout=2,
    broker_socket_connect_timeout=2,
)

# Set connection pool parameters
app.conf.broker_pool_limit = 1
app.conf.broker_connection_retry_on_startup = False
