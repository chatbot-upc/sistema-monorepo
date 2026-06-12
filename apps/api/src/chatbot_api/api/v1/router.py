from fastapi import APIRouter

from .endpoints import (
    admin_devices,
    auth,
    conversations,
    documents,
    intents,
    monitoring,
    notifications,
    prompts,
    reports,
)

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth.router)
api_v1_router.include_router(admin_devices.router)
api_v1_router.include_router(conversations.router)
api_v1_router.include_router(documents.router)
api_v1_router.include_router(intents.router)
api_v1_router.include_router(monitoring.router)
api_v1_router.include_router(notifications.router)
api_v1_router.include_router(prompts.router)
api_v1_router.include_router(reports.router)
