from fastapi import APIRouter

from app.api.routes import auth, dropbox, integrations, one_drive, search, utils, ws

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(ws.router)
api_router.include_router(utils.router)
api_router.include_router(integrations.router)
api_router.include_router(one_drive.router)
api_router.include_router(dropbox.router)
api_router.include_router(search.router)
