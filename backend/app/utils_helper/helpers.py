import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional


def generate_uuid() -> str:
    return str(uuid.uuid4())


def generate_hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def get_current_timestamp() -> datetime:
    return datetime.utcnow()


def add_time(hours: int = 0, minutes: int = 0, days: int = 0) -> datetime:
    return datetime.utcnow() + timedelta(hours=hours, minutes=minutes, days=days)


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    return dt.strftime(fmt)


def parse_datetime(dt_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    return datetime.strptime(dt_str, fmt)
