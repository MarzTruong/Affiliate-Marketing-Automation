"""Telegram channel publisher via Bot API."""

import httpx

from backend.config import settings
from backend.affiliate.publishers.base import BasePublisher, PublishResult


class TelegramPublisher(BasePublisher):
    """Publish messages to a Telegram channel using the Bot API."""

    BOT_API = "https://api.telegram.org"

    def __init__(self, bot_token: str | None = None, channel_id: str | None = None):
        self.bot_token = bot_token or settings.telegram_bot_token
        self.channel_id = channel_id or settings.telegram_channel_id

    @property
    def platform_name(self) -> str:
        return "telegram"

    async def publish(self, title: str, body: str, **kwargs) -> PublishResult:
        link = kwargs.get("link")
        text = f"<b>{title}</b>\n\n{body}"
        if link:
            text += f'\n\n<a href="{link}">Xem sản phẩm</a>'

        payload = {
            "chat_id": self.channel_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": kwargs.get("disable_preview", False),
        }

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    f"{self.BOT_API}/bot{self.bot_token}/sendMessage",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("ok"):
                    msg_id = str(data["result"]["message_id"])
                    return PublishResult(success=True, external_post_id=msg_id)
                return PublishResult(success=False, error=data.get("description", "Unknown error"))
            except httpx.HTTPStatusError as e:
                return PublishResult(success=False, error=f"Telegram API error: {e.response.text}")
            except Exception as e:
                return PublishResult(success=False, error=str(e))

    async def delete(self, external_post_id: str) -> bool:
        payload = {
            "chat_id": self.channel_id,
            "message_id": int(external_post_id),
        }
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    f"{self.BOT_API}/bot{self.bot_token}/deleteMessage",
                    json=payload,
                )
                data = resp.json()
                return data.get("ok", False)
            except Exception:
                return False

    async def health_check(self) -> bool:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(f"{self.BOT_API}/bot{self.bot_token}/getMe")
                data = resp.json()
                return data.get("ok", False)
            except Exception:
                return False
