from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings


def setup_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"]
    )
