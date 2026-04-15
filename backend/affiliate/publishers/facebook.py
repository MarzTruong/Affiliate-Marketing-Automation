"""Facebook Page publisher via Graph API."""

import httpx

from backend.config import settings
from backend.affiliate.publishers.base import BasePublisher, PublishResult


class FacebookPublisher(BasePublisher):
    """Publish posts to a Facebook Page using the Graph API."""

    GRAPH_API = "https://graph.facebook.com/v19.0"

    def __init__(self, page_id: str | None = None, access_token: str | None = None):
        self.page_id = page_id or settings.facebook_page_id
        self.access_token = access_token or settings.facebook_access_token

    @property
    def platform_name(self) -> str:
        return "facebook"

    async def publish(self, title: str, body: str, **kwargs) -> PublishResult:
        link = kwargs.get("link")
        message = f"{title}\n\n{body}"
        if link:
            message += f"\n\n{link}"

        payload = {"message": message, "access_token": self.access_token}

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    f"{self.GRAPH_API}/{self.page_id}/feed",
                    data=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                post_id = data.get("id", "")
                return PublishResult(
                    success=True,
                    external_post_id=post_id,
                    url=f"https://facebook.com/{post_id}",
                )
            except httpx.HTTPStatusError as e:
                return PublishResult(success=False, error=f"Facebook API error: {e.response.text}")
            except Exception as e:
                return PublishResult(success=False, error=str(e))

    async def delete(self, external_post_id: str) -> bool:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.delete(
                    f"{self.GRAPH_API}/{external_post_id}",
                    params={"access_token": self.access_token},
                )
                return resp.is_success
            except Exception:
                return False

    async def health_check(self) -> bool:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(
                    f"{self.GRAPH_API}/{self.page_id}",
                    params={"access_token": self.access_token, "fields": "id"},
                )
                return resp.is_success
            except Exception:
                return False
