from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/utils", tags=["utils"])


@router.get("/health-check", status_code=200)
async def health_check(request: Request):
    """Basic health-check endpoint. Returns service status and redis probe if available."""
    result = {"status": "ok"}
    redis = getattr(request.app.state, "redis", None)
    try:
        if redis:
            pong = await redis.ping()
            result["redis"] = bool(pong)
        else:
            result["redis"] = None
    except Exception:
        result["redis"] = False
    return JSONResponse(result)
