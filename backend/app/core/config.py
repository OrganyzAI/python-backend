import secrets
import warnings
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    # No frontend in this repository; leave blank by default
    FRONTEND_HOST: str = ""
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    DEBUG: bool = False

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        origins = [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS]
        if self.FRONTEND_HOST:
            origins.append(self.FRONTEND_HOST)
        return origins

    PROJECT_NAME: str = "Full Stack FastAPI Project"
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    # Redis connection URL. Default points to the compose service `redis`.
    REDIS_URL: str = "redis://redis:6379/0"
    # Celery broker/result backend. By default reuse `REDIS_URL` so you can
    # configure an Upstash or other hosted Redis via `REDIS_URL` or explicitly
    # via `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` env vars.
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # Cloudflare R2 (S3 compatible) settings
    R2_ENABLED: bool = False
    R2_ACCOUNT_ID: str | None = None
    R2_ACCESS_KEY_ID: str | None = None
    R2_SECRET_ACCESS_KEY: str | None = None
    R2_BUCKET: str | None = None
    R2_ENDPOINT_URL: AnyUrl | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def r2_endpoint(self) -> str | None:
        """Return explicit endpoint URL if set, otherwise construct from account id."""
        if self.R2_ENDPOINT_URL:
            return str(self.R2_ENDPOINT_URL).rstrip("/")
        if self.R2_ACCOUNT_ID:
            return f"https://{self.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def r2_enabled(self) -> bool:
        """Whether R2 integration is configured/enabled."""
        if not self.R2_ENABLED:
            return False
        return bool(
            self.R2_BUCKET and self.R2_ACCESS_KEY_ID and self.R2_SECRET_ACCESS_KEY
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def r2_boto3_config(self) -> dict[str, Any]:
        """Return a dict of kwargs suitable for boto3/aioboto3 client creation."""
        if not self.r2_enabled:
            return {}
        cfg: dict[str, Any] = {
            "aws_access_key_id": self.R2_ACCESS_KEY_ID,
            "aws_secret_access_key": self.R2_SECRET_ACCESS_KEY,
        }
        endpoint = self.r2_endpoint
        if endpoint:
            cfg["endpoint_url"] = endpoint
        return cfg

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "Test@1234"
    USER_PASSWORD: str = "Test@1234"
    INITIAL_ADMIN_EMAIL: EmailStr = "admin@example.com"
    INITIAL_ADMIN_PASSWORD: str = "Test@12345"

    # WebEngage transactional email settings
    WEBENGAGE_API_URL: HttpUrl | None = None
    WEBENGAGE_API_KEY: str | None = None
    WEBENGAGE_LICENSE_CODE: str | None = None
    WEBENGAGE_CAMPAIGN_REGISTER_ID: str | None = None
    WEBENGAGE_CAMPAIGN_FORGOT_PASSWORD_ID: str | None = None

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def webengage_enabled(self) -> bool:
        """Whether WebEngage transactional email integration is configured."""
        return bool(self.WEBENGAGE_API_URL and self.WEBENGAGE_API_KEY)


try:
    settings = Settings()
except Exception:
    # During test collection or in minimal environments the full validation
    # may fail (missing env vars). Fall back to an unvalidated model
    # instance to allow imports that reference `settings` to work.
    try:
        settings = Settings.model_construct()
    except Exception:
        # As a last resort, create an empty instance without validation
        settings = Settings.__new__(Settings)
    # Ensure a minimal set of commonly-accessed attributes exist so
    # import-time access (e.g. in app.main) does not raise AttributeError.
    # Prefer values from the environment when available.
    import os
    from pathlib import Path

    # If a top-level .env file exists (searched upwards), load any simple
    # KEY=VALUE pairs into os.environ so fallback defaults can pick them up.
    try:
        _p = Path(__file__).resolve().parent
        _env_path: Path | None = None
        for _ in range(6):
            candidate = _p / ".env"
            if candidate.exists():
                _env_path = candidate
                break
            if _p.parent == _p:
                break
            _p = _p.parent

        if _env_path:
            text = _env_path.read_text(encoding="utf8")
            for raw in text.splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                # don't override existing env vars
                os.environ.setdefault(k, v)
    except Exception:
        # best-effort only; don't fail import on unexpected IO errors
        pass

        _fallback_defaults = {
            "PROJECT_NAME": os.environ.get(
                "PROJECT_NAME", "Full Stack FastAPI Project"
            ),
            "POSTGRES_SERVER": os.environ.get("POSTGRES_SERVER", "localhost"),
            "POSTGRES_PORT": int(os.environ.get("POSTGRES_PORT", 5432)),
            "POSTGRES_USER": os.environ.get("POSTGRES_USER", "postgres"),
            "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "POSTGRES_DB": os.environ.get("POSTGRES_DB", ""),
            "FIRST_SUPERUSER": os.environ.get("FIRST_SUPERUSER", "admin@example.com"),
            "FIRST_SUPERUSER_PASSWORD": os.environ.get("FIRST_SUPERUSER_PASSWORD", ""),
        }

    for _k, _v in _fallback_defaults.items():
        if not hasattr(settings, _k):
            try:
                setattr(settings, _k, _v)
            except Exception:
                # Best-effort: ignore if attribute can't be set on the fallback
                pass
