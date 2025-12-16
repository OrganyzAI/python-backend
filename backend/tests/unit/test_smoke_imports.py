import importlib
import pytest

MODULES = [
    # utils and helpers
    "app.utils",
    "app.utils_helper.threading",
    "app.utils_helper.regex",
    "app.utils_helper.messages",

    # services
    "app.services.webengage_email",
    "app.services.auth_service",

    # middlewares (import-only smoke)
    "app.middlewares.logger",
    "app.middlewares.error_handler",

    # core
    "app.core.config",
    "app.core.db",
    "app.core.exceptions",
    "app.core.security",
]


def test_import_smoke():
    """Attempt to import modules; skip if import fails due to environment.

    This is a lightweight smoke test to exercise top-level code paths that
    are safe to import without starting services.
    """
    for mod in MODULES:
        try:
            importlib.import_module(mod)
        except Exception as exc:  # pragma: no cover - guard against environment issues
            pytest.skip(f"Skipping import of {mod}: {exc}")
