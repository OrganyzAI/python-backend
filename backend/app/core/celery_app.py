from __future__ import annotations

from celery import Celery  # type: ignore[import-untyped]

from app.core.config import settings


broker_url = settings.CELERY_BROKER_URL or settings.REDIS_URL
result_backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL


celery_app = Celery(
    settings.PROJECT_NAME if getattr(settings, "PROJECT_NAME", None) else "app",
    broker=broker_url,
    backend=result_backend,
)


celery_app.conf.update(
    result_expires=3600,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

celery_app.autodiscover_tasks(["app.workers"])
