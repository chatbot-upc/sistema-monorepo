from fastapi import APIRouter

from .endpoints import auth, conversations, documents, intents, notifications, reports

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth.router)
api_v1_router.include_router(conversations.router)
api_v1_router.include_router(documents.router)
api_v1_router.include_router(intents.router)
api_v1_router.include_router(notifications.router)
api_v1_router.include_router(reports.router)
