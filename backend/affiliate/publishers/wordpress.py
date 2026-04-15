"""WordPress publisher via REST API."""

import httpx

from backend.config import settings
from backend.affiliate.publishers.base import BasePublisher, PublishResult


class WordPressPublisher(BasePublisher):
    """Publish posts to a WordPress site using the WP REST API."""

    def __init__(
        self,
        site_url: str | None = None,
        username: str | None = None,
        app_password: str | None = None,
    ):
        self.site_url = (site_url or settings.wordpress_site_url).rstrip("/")
        self.username = username or settings.wordpress_username
        self.app_password = app_password or settings.wordpress_app_password

    @property
    def platform_name(self) -> str:
        return "wordpress"

    async def publish(self, title: str, body: str, **kwargs) -> PublishResult:
        categories = kwargs.get("categories", [])
        tags = kwargs.get("tags", [])
        status = kwargs.get("wp_status", "publish")

        payload = {
            "title": title,
            "content": body,
            "status": status,
        }
        if categories:
            payload["categories"] = categories
        if tags:
            payload["tags"] = tags

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    f"{self.site_url}/wp-json/wp/v2/posts",
                    json=payload,
                    auth=(self.username, self.app_password),
                )
                resp.raise_for_status()
                data = resp.json()
                return PublishResult(
                    success=True,
                    external_post_id=str(data["id"]),
                    url=data.get("link", ""),
                )
            except httpx.HTTPStatusError as e:
                return PublishResult(success=False, error=f"WordPress API error: {e.response.text}")
            except Exception as e:
                return PublishResult(success=False, error=str(e))

    async def delete(self, external_post_id: str) -> bool:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.delete(
                    f"{self.site_url}/wp-json/wp/v2/posts/{external_post_id}",
                    params={"force": True},
                    auth=(self.username, self.app_password),
                )
                return resp.is_success
            except Exception:
                return False

    async def health_check(self) -> bool:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(f"{self.site_url}/wp-json/wp/v2/posts?per_page=1")
                return resp.is_success
            except Exception:
                return False
