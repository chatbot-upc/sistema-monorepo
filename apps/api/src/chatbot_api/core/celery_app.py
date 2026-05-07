"""Celery app for async tasks (ingest_document, future workers)."""

from celery import Celery

from .settings import get_settings

_settings = get_settings()

celery_app = Celery(
    "chatbot_api",
    broker=_settings.celery_broker_url,
    backend=_settings.celery_result_backend,
    include=["chatbot_api.workers.ingest"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=600,
    worker_prefetch_multiplier=1,
)
