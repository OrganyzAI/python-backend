import logging
from typing import Any

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.add")  # type: ignore[misc]
def add(x: int, y: int) -> int:
    return x + y


@celery_app.task(name="tasks.send_welcome_email")  # type: ignore[misc]
def send_welcome_email(email: str, context: dict[str, Any] | None = None) -> None:
    logger.info("Sending welcome email to %s with context %s", email, context)
    return None


__all__ = ["add", "send_welcome_email"]
