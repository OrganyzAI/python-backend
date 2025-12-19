import logging

from sqlalchemy import Engine
from sqlmodel import Session, select
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

from app.core import security
from app.core.db import get_engine
from app.enums.user_enum import UserRole, UserStatus
from app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

max_tries = 60 * 5  # 5 minutes
wait_seconds = 1


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
def init(db_engine: Engine) -> None:
    try:
        with Session(db_engine) as session:
            session.exec(select(1))
    except Exception as e:
        logger.error(e)
        raise e


def ensure_initial_admin(db_engine: Engine) -> None:
    """
    Ensure a default admin user exists.

    If a user with the hardcoded admin email already exists, this is a no-op.
    Otherwise, create it with the specified credentials.
    """
    admin_email = "admin@admin.com"
    admin_password = "Password@1234"

    with Session(db_engine) as session:
        existing_admin = session.exec(
            select(User).where(User.email == admin_email)
        ).first()

        if existing_admin:
            logger.info("Admin user already exists, skipping creation.")
            return

        hashed_password = security.get_password_hash(admin_password)
        admin_user = User(
            email=admin_email,
            hashed_password=hashed_password,
            status=UserStatus.active,
            role=UserRole.admin,
        )

        session.add(admin_user)
        session.commit()
        session.refresh(admin_user)
        logger.info("Initial admin user created: %s", admin_email)


def main() -> None:
    logger.info("Initializing service")
    engine = get_engine()
    init(engine)
    ensure_initial_admin(engine)
    logger.info("Service finished initializing")


if __name__ == "__main__":
    main()
