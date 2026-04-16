from fastapi import APIRouter

from backend.api.v1.analytics import router as analytics_router
from backend.api.v1.auth import router as auth_router
from backend.api.v1.automation import router as automation_router
from backend.api.v1.calendar import router as calendar_router
from backend.api.v1.campaigns import router as campaigns_router
from backend.api.v1.chat import router as chat_router
from backend.api.v1.content import router as content_router
from backend.api.v1.notifications import router as notifications_router
from backend.api.v1.platforms import router as platforms_router
from backend.api.v1.publisher import router as publisher_router
from backend.api.v1.sop import router as sop_router
from backend.api.v1.settings import router as settings_router
from backend.api.v1.system import router as system_router
from backend.api.v1.webhooks import router as webhooks_router
from backend.tiktok.router import router as tiktok_studio_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(campaigns_router, prefix="/campaigns", tags=["campaigns"])
router.include_router(content_router, prefix="/content", tags=["content"])
router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
router.include_router(platforms_router, prefix="/platforms", tags=["platforms"])
router.include_router(publisher_router, prefix="/publisher", tags=["publisher"])
router.include_router(sop_router, prefix="/sop", tags=["sop"])
router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
router.include_router(system_router, prefix="/system", tags=["system"])
router.include_router(automation_router, prefix="/automation", tags=["automation"])
router.include_router(calendar_router, prefix="/calendar", tags=["calendar"])
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(settings_router, prefix="/settings", tags=["settings"])
router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
router.include_router(tiktok_studio_router, prefix="/tiktok-studio", tags=["tiktok-studio"])
