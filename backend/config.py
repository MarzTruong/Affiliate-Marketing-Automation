import logging
from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Các key platform KHÔNG đọc từ .env — được load từ DB qua apply_db_settings()
PLATFORM_SETTING_KEYS = {
    "CLAUDE_DAILY_COST_LIMIT_USD",
    "FACEBOOK_PAGE_ID",
    "FACEBOOK_ACCESS_TOKEN",
    "WORDPRESS_SITE_URL",
    "WORDPRESS_USERNAME",
    "WORDPRESS_APP_PASSWORD",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHANNEL_ID",
    "TIKTOK_ACCESS_TOKEN",
    "TIKTOK_APP_KEY",
    "TIKTOK_APP_SECRET",
    "SHOPEE_PARTNER_ID",
    "SHOPEE_PARTNER_KEY",
    "SHOPEE_ACCESS_TOKEN",
    "SHOPEE_SHOP_ID",
    "SHOPBACK_PARTNER_ID",
    "SHOPBACK_API_KEY",
    "ACCESSTRADE_API_KEY",
    "ACCESSTRADE_SITE_ID",
    "BANNERBEAR_API_KEY",
    "BANNERBEAR_DEFAULT_TEMPLATE_ID",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",
    "HEYGEN_API_KEY",
    "HEYGEN_AVATAR_ID",
    "HEYGEN_VOICE_ID",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "affiliate-marketing-automation"
    app_env: str = "development"
    debug: bool = True

    # Database — luôn đọc từ .env
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/affiliate_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Anthropic — đọc từ .env (critical key, không lưu DB)
    anthropic_api_key: str = ""

    # Google Gemini — đọc từ .env (critical key, không lưu DB)
    gemini_api_key: str = ""

    # ── Platform credentials: default rỗng, được overlay từ DB khi startup ──
    claude_daily_cost_limit_usd: Decimal = Decimal("20.00")

    # Facebook
    facebook_page_id: str = ""
    facebook_access_token: str = ""
    facebook_webhook_secret: str = ""  # HMAC secret để verify webhook signature
    facebook_webhook_verify_token: str = (
        "affiliate_webhook_verify"  # Token xác minh khi đăng ký webhook
    )

    # WordPress
    wordpress_site_url: str = ""
    wordpress_username: str = ""
    wordpress_app_password: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_channel_id: str = ""

    # TikTok
    tiktok_app_key: str = ""
    tiktok_app_secret: str = ""
    tiktok_access_token: str = ""

    # Shopee
    shopee_partner_id: str = ""
    shopee_partner_key: str = ""
    shopee_access_token: str = ""
    shopee_shop_id: str = ""

    # ShopBack
    shopback_partner_id: str = ""
    shopback_api_key: str = ""

    # AccessTrade
    accesstrade_api_key: str = ""
    accesstrade_site_id: str = ""

    # Bannerbear
    bannerbear_api_key: str = ""
    bannerbear_default_template_id: str = ""

    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""  # Voice ID sau khi clone giọng trên ElevenLabs

    # HeyGen
    heygen_api_key: str = ""
    heygen_avatar_id: str = ""  # Avatar ID trên HeyGen (Photo Avatar / Digital Twin)
    heygen_voice_id: str = ""  # Voice ID trên HeyGen để sync môi avatar

    # Fal.ai (Kling AI video generation) — đọc từ .env
    fal_key: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()

# Map DB key → tên field trên settings object
_DB_KEY_TO_FIELD: dict[str, str] = {k: k.lower() for k in PLATFORM_SETTING_KEYS}


async def apply_db_settings() -> None:
    """Nạp platform credentials từ bảng system_settings vào settings singleton.

    Gọi một lần trong app lifespan sau khi DB sẵn sàng.
    Chỉ override các platform keys — không chạm DATABASE_URL và ANTHROPIC_API_KEY.
    """
    from sqlalchemy import select

    from backend.database import async_session
    from backend.models.system_settings import SystemSettings

    try:
        async with async_session() as db:
            rows = await db.execute(select(SystemSettings))
            db_settings = {row.key: row.value for row in rows.scalars()}

        count = 0
        for db_key, field_name in _DB_KEY_TO_FIELD.items():
            if db_key in db_settings and db_settings[db_key]:
                raw = db_settings[db_key]
                # Convert sang đúng kiểu dữ liệu của field
                if db_key == "CLAUDE_DAILY_COST_LIMIT_USD":
                    try:
                        raw = Decimal(raw)
                    except Exception:
                        logger.warning(f"[Settings] Giá trị không hợp lệ cho {db_key}: {raw!r}")
                        continue
                object.__setattr__(settings, field_name, raw)
                count += 1

        if count:
            logger.info(f"[Settings] Nạp {count} credentials từ DB thành công.")
    except Exception as e:
        logger.warning(f"[Settings] Không thể nạp settings từ DB: {e}. Dùng giá trị từ .env.")
