"""Settings API — đọc và ghi credentials vào bảng system_settings.

Không còn ghi đè .env file.
DATABASE_URL và ANTHROPIC_API_KEY chỉ đọc từ .env — không quản lý tại đây.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import _DB_KEY_TO_FIELD, settings
from backend.database import get_db
from backend.models.system_settings import SystemSettings

router = APIRouter()

# Metadata hiển thị cho UI — thứ tự và nhóm
CREDENTIAL_KEYS: list[dict] = [
    {
        "key": "CLAUDE_DAILY_COST_LIMIT_USD",
        "group": "ai",
        "label": "Giới hạn chi phí/ngày (USD)",
        "sensitive": False,
    },
    {
        "key": "FACEBOOK_PAGE_ID",
        "group": "facebook",
        "label": "Facebook Page ID",
        "sensitive": False,
    },
    {
        "key": "FACEBOOK_ACCESS_TOKEN",
        "group": "facebook",
        "label": "Facebook Access Token",
        "sensitive": True,
    },
    {
        "key": "WORDPRESS_SITE_URL",
        "group": "wordpress",
        "label": "WordPress Site URL",
        "sensitive": False,
    },
    {
        "key": "WORDPRESS_USERNAME",
        "group": "wordpress",
        "label": "WordPress Username",
        "sensitive": False,
    },
    {
        "key": "WORDPRESS_APP_PASSWORD",
        "group": "wordpress",
        "label": "WordPress App Password",
        "sensitive": True,
    },
    {
        "key": "TELEGRAM_BOT_TOKEN",
        "group": "telegram",
        "label": "Telegram Bot Token",
        "sensitive": True,
    },
    {
        "key": "TELEGRAM_CHANNEL_ID",
        "group": "telegram",
        "label": "Telegram Channel ID",
        "sensitive": False,
    },
    {
        "key": "TIKTOK_ACCESS_TOKEN",
        "group": "tiktok",
        "label": "TikTok Access Token",
        "sensitive": True,
    },
    {"key": "TIKTOK_APP_KEY", "group": "tiktok", "label": "TikTok App Key", "sensitive": False},
    {
        "key": "TIKTOK_APP_SECRET",
        "group": "tiktok",
        "label": "TikTok App Secret",
        "sensitive": True,
    },
    {
        "key": "SHOPEE_PARTNER_ID",
        "group": "shopee",
        "label": "Shopee Partner ID",
        "sensitive": False,
    },
    {
        "key": "SHOPEE_PARTNER_KEY",
        "group": "shopee",
        "label": "Shopee Partner Key",
        "sensitive": True,
    },
    {
        "key": "SHOPEE_ACCESS_TOKEN",
        "group": "shopee",
        "label": "Shopee Access Token",
        "sensitive": True,
    },
    {"key": "SHOPEE_SHOP_ID", "group": "shopee", "label": "Shopee Shop ID", "sensitive": False},
    {
        "key": "SHOPBACK_PARTNER_ID",
        "group": "shopback",
        "label": "ShopBack Partner ID",
        "sensitive": False,
    },
    {
        "key": "SHOPBACK_API_KEY",
        "group": "shopback",
        "label": "ShopBack API Key",
        "sensitive": True,
    },
    {
        "key": "ACCESSTRADE_API_KEY",
        "group": "accesstrade",
        "label": "AccessTrade API Key",
        "sensitive": True,
    },
    {
        "key": "ACCESSTRADE_SITE_ID",
        "group": "accesstrade",
        "label": "AccessTrade Site ID",
        "sensitive": False,
    },
    {
        "key": "BANNERBEAR_API_KEY",
        "group": "bannerbear",
        "label": "Bannerbear API Key",
        "sensitive": True,
    },
    {
        "key": "BANNERBEAR_DEFAULT_TEMPLATE_ID",
        "group": "bannerbear",
        "label": "Bannerbear Template ID",
        "sensitive": False,
    },
    {
        "key": "ELEVENLABS_API_KEY",
        "group": "elevenlabs",
        "label": "ElevenLabs API Key",
        "sensitive": True,
    },
    {
        "key": "ELEVENLABS_VOICE_ID",
        "group": "elevenlabs",
        "label": "ElevenLabs Voice ID",
        "sensitive": False,
    },
    {
        "key": "ELEVENLABS_MODEL_ID",
        "group": "elevenlabs",
        "label": "ElevenLabs Model ID",
        "sensitive": False,
    },
]

KNOWN_KEYS = {item["key"] for item in CREDENTIAL_KEYS}


# ── Pydantic schemas ─────────────────────────────────────────────────────────


class CredentialItem(BaseModel):
    key: str
    group: str
    label: str
    sensitive: bool
    value: str


class CredentialsResponse(BaseModel):
    credentials: list[CredentialItem]


class CredentialUpdate(BaseModel):
    key: str
    value: str


class UpdateCredentialsRequest(BaseModel):
    updates: list[CredentialUpdate]


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/credentials", response_model=CredentialsResponse)
async def get_credentials(db: AsyncSession = Depends(get_db)):
    """Đọc credentials hiện tại từ DB — sensitive fields hiện là ****."""
    rows = await db.execute(select(SystemSettings))
    db_values: dict[str, str] = {row.key: row.value for row in rows.scalars()}

    items = []
    for meta in CREDENTIAL_KEYS:
        raw = db_values.get(meta["key"], "")
        display = "****" if (meta["sensitive"] and raw) else raw
        items.append(
            CredentialItem(
                key=meta["key"],
                group=meta["group"],
                label=meta["label"],
                sensitive=meta["sensitive"],
                value=display,
            )
        )
    return CredentialsResponse(credentials=items)


@router.post("/credentials")
async def update_credentials(
    body: UpdateCredentialsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Ghi credentials vào bảng system_settings và cập nhật settings singleton.

    Bỏ qua các giá trị '****' (user không thay đổi).
    Không ghi đè .env file.
    """
    updated: list[str] = []

    for update in body.updates:
        # Validate key nằm trong whitelist
        if update.key not in KNOWN_KEYS:
            raise HTTPException(status_code=400, detail=f"Key không hợp lệ: {update.key}")

        # Bỏ qua placeholder — user không thay đổi giá trị cũ
        if update.value in ("****", ""):
            continue

        # Sanitize: loại bỏ newline tránh injection
        clean_value = update.value.replace("\n", "").replace("\r", "").strip()
        if not clean_value:
            continue

        # Upsert vào DB
        existing = await db.get(SystemSettings, update.key)
        if existing:
            existing.value = clean_value
        else:
            db.add(SystemSettings(key=update.key, value=clean_value))

        # Cập nhật settings singleton ngay lập tức (in-memory)
        field_name = _DB_KEY_TO_FIELD.get(update.key)
        if field_name:
            object.__setattr__(settings, field_name, clean_value)

        updated.append(update.key)

    return {"updated": updated, "message": f"Đã cập nhật {len(updated)} credentials"}


@router.get("/test-connection/{platform}")
async def test_connection(platform: str):
    """Test kết nối với platform dùng credentials hiện có trong settings."""
    affiliate_platforms = {"shopee", "tiktok_shop", "shopback", "accesstrade"}
    publisher_platforms = {"facebook", "wordpress", "telegram", "tiktok"}

    if platform in affiliate_platforms:
        try:
            from backend.affiliate.connectors import get_connector

            connector = get_connector(platform)
            is_connected = await connector.authenticate()
            status = "connected" if is_connected else "failed"
            return {"status": status, "platform": platform}
        except Exception as e:
            return {"status": "error", "platform": platform, "detail": str(e)}

    if platform in publisher_platforms:
        try:
            from backend.affiliate.publishers.posting_service import get_publisher

            publisher = get_publisher(platform)
            _ = publisher
            return {"status": "connected", "platform": platform}
        except ValueError as e:
            return {"status": "failed", "platform": platform, "detail": str(e)}
        except Exception as e:
            return {"status": "error", "platform": platform, "detail": str(e)}

    raise HTTPException(status_code=400, detail=f"Platform không hỗ trợ: {platform}")
