import warnings
import pytest
from pathlib import Path
from pydantic import ValidationError
from app.core.config import Settings, parse_cors


def _base_kwargs():
    return {
        "PROJECT_NAME": "Proj",
        "POSTGRES_SERVER": "localhost",
        "POSTGRES_USER": "user",
        "POSTGRES_DB": "db",
        "FIRST_SUPERUSER": "admin@example.com",
        "FIRST_SUPERUSER_PASSWORD": "secretpw",
    }


def test_all_cors_origins_and_default_emails_from():
    kw = _base_kwargs()
    kw.update({
        "BACKEND_CORS_ORIGINS": "http://a.com, http://b.com/",
        "FRONTEND_HOST": "https://frontend.local",
        # omit EMAILS_FROM_NAME to exercise _set_default_emails_from
    })
    s = Settings(**kw)
    origins = s.all_cors_origins
    assert "http://a.com" in origins
    assert "http://b.com" in origins
    assert "https://frontend.local" in origins
    assert s.EMAILS_FROM_NAME == "Proj"


def test_sqlalchemy_uri_and_emails_webengage():
    kw = _base_kwargs()
    kw.update({
        "POSTGRES_PORT": 5433,
        "POSTGRES_PASSWORD": "pw",
        "SMTP_HOST": "smtp.local",
        "EMAILS_FROM_EMAIL": "from@example.com",
        "WEBENGAGE_API_URL": "https://api.webengage.test",
        "WEBENGAGE_API_KEY": "key",
    })
    s = Settings(**kw)
    uri = s.SQLALCHEMY_DATABASE_URI
    assert "postgresql+psycopg" in str(uri)
    assert s.emails_enabled is True
    assert s.webengage_enabled is True


def test_r2_endpoint_and_boto3_config():
    kw = _base_kwargs()
    # explicit endpoint
    kw.update({
        "R2_ENDPOINT_URL": "https://custom.endpoint",
        "R2_ENABLED": True,
        "R2_BUCKET": "b",
        "R2_ACCESS_KEY_ID": "id",
        "R2_SECRET_ACCESS_KEY": "secret",
    })
    s = Settings(**kw)
    assert s.r2_endpoint == "https://custom.endpoint"
    assert s.r2_enabled is True
    cfg = s.r2_boto3_config
    assert cfg.get("aws_access_key_id") == "id"
    assert cfg.get("endpoint_url") == "https://custom.endpoint"

    # account id fallback
    kw2 = _base_kwargs()
    kw2.update({"R2_ACCOUNT_ID": "acct-123"})
    s2 = Settings(**kw2)
    assert s2.r2_endpoint == "https://acct-123.r2.cloudflarestorage.com"
    assert s2.r2_enabled is False
    # when disabled, boto3 config should be empty
    assert s2.r2_boto3_config == {}


def test_default_secrets_warning_local_and_error_nonlocal():
    # local environment: changethis should warn but not raise
    kw = _base_kwargs()
    kw.update({"SECRET_KEY": "changethis", "POSTGRES_PASSWORD": "changethis", "FIRST_SUPERUSER_PASSWORD": "changethis"})
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        s = Settings(**kw)
        # validator runs and should not raise in local
        assert any("changethis" in str(x.message) for x in w)

    # non-local should raise ValueError during model validation
    kw2 = _base_kwargs()
    kw2.update({"ENVIRONMENT": "production", "SECRET_KEY": "changethis", "POSTGRES_PASSWORD": "changethis", "FIRST_SUPERUSER_PASSWORD": "changethis"})
    with pytest.raises(ValueError):
        Settings(**kw2)


def test_parse_cors_list_and_invalid():
    # list input should be returned as-is
    assert parse_cors(["http://x"]) == ["http://x"]

    # invalid type should raise
    with pytest.raises(ValueError):
        parse_cors(123)


def test_import_module_fallbacks(monkeypatch):
    # Ensure no required env vars are present for a fresh import
    for k in (
        "PROJECT_NAME",
        "POSTGRES_SERVER",
        "POSTGRES_USER",
        "POSTGRES_DB",
        "FIRST_SUPERUSER",
        "FIRST_SUPERUSER_PASSWORD",
    ):
        monkeypatch.delenv(k, raising=False)

    src_path = Path(__file__).resolve().parents[2] / "app" / "core" / "config.py"
    src = src_path.read_text()

    # Inject code to force Settings() and Settings.model_construct() to raise,
    # so the final fallback (Settings.__new__) runs.
    marker = "try:\n    settings = Settings()"
    assert marker in src
    inject = (
        "\n# injected to force Settings() and model_construct to raise\n"
        "Settings.__init__ = lambda self, *a, **k: (_ for _ in ()).throw(Exception('boom'))\n"
        "Settings.model_construct = classmethod(lambda cls: (_ for _ in ()).throw(Exception('boom')))\n"
    )
    new_src = src.replace(marker, inject + marker)

    namespace: dict = {}
    exec(compile(new_src, str(src_path), "exec"), namespace)

    # final fallback should assign `settings` in the module namespace
    assert "settings" in namespace
    settings_obj = namespace["settings"]
    assert isinstance(settings_obj, namespace["Settings"])  # created via __new__
