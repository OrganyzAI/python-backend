from fastapi import APIRouter

from app.api.routes import auth, ws, utils

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(ws.router)
api_router.include_router(utils.router)
