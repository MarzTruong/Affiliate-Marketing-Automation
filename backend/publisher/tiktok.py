"""TikTok publisher via Content Posting API v2."""

import httpx

from backend.config import settings
from backend.publisher.base import BasePublisher, PublishResult


class TikTokPublisher(BasePublisher):
    """Publish video/caption content to TikTok via Content Posting API.

    Supports:
    - Direct post (video URL) via PUBLISH_VIDEO endpoint
    - Caption-only draft (inbox post) for manual video upload
    """

    API_BASE = "https://open.tiktokapis.com/v2"

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token or settings.tiktok_access_token

    @property
    def platform_name(self) -> str:
        return "tiktok"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    async def publish(self, title: str, body: str, **kwargs) -> PublishResult:
        """Post content to TikTok.

        kwargs:
            video_url (str): Public video URL to upload. If omitted, creates a draft caption.
            privacy_level (str): "PUBLIC_TO_EVERYONE" | "MUTUAL_FOLLOW_FRIENDS" | "SELF_ONLY"
            disable_comment (bool): Default False.
            disable_duet (bool): Default False.
            disable_stitch (bool): Default False.
        """
        if not self.access_token:
            return PublishResult(
                success=False,
                error="TikTok access token not configured. Set TIKTOK_ACCESS_TOKEN in .env",
            )

        video_url = kwargs.get("video_url")
        privacy_level = kwargs.get("privacy_level", "SELF_ONLY")

        caption = f"{title}\n\n{body}"
        if len(caption) > 2200:
            caption = caption[:2197] + "..."

        if video_url:
            return await self._publish_video(caption, video_url, privacy_level, kwargs)
        else:
            return await self._create_draft(caption, privacy_level)

    async def _publish_video(
        self, caption: str, video_url: str, privacy_level: str, kwargs: dict
    ) -> PublishResult:
        payload = {
            "post_info": {
                "title": caption,
                "privacy_level": privacy_level,
                "disable_comment": kwargs.get("disable_comment", False),
                "disable_duet": kwargs.get("disable_duet", False),
                "disable_stitch": kwargs.get("disable_stitch", False),
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
            },
        }

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                resp = await client.post(
                    f"{self.API_BASE}/post/publish/video/init/",
                    json=payload,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("error", {}).get("code") == "ok":
                    post_id = data.get("data", {}).get("publish_id", "")
                    return PublishResult(success=True, external_post_id=post_id)
                err = data.get("error", {}).get("message", "Unknown TikTok error")
                return PublishResult(success=False, error=err)
            except httpx.HTTPStatusError as e:
                return PublishResult(success=False, error=f"TikTok API {e.response.status_code}: {e.response.text[:200]}")
            except Exception as e:
                return PublishResult(success=False, error=str(e))

    async def _create_draft(self, caption: str, privacy_level: str) -> PublishResult:
        """Create an inbox draft (no video required — for manual upload later)."""
        payload = {
            "post_info": {
                "title": caption,
                "privacy_level": privacy_level,
                "disable_comment": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": 0,
                "chunk_size": 0,
                "total_chunk_count": 0,
            },
            "post_mode": "INBOX",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    f"{self.API_BASE}/post/publish/inbox/video/init/",
                    json=payload,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("error", {}).get("code") == "ok":
                    publish_id = data.get("data", {}).get("publish_id", "draft")
                    return PublishResult(
                        success=True,
                        external_post_id=publish_id,
                        url="https://www.tiktok.com/creator#inbox",
                    )
                err = data.get("error", {}).get("message", "Unknown TikTok error")
                return PublishResult(success=False, error=err)
            except httpx.HTTPStatusError as e:
                return PublishResult(success=False, error=f"TikTok API {e.response.status_code}: {e.response.text[:200]}")
            except Exception as e:
                return PublishResult(success=False, error=str(e))

    async def delete(self, external_post_id: str) -> bool:
        # TikTok Content Posting API does not support deletion via API
        return False

    async def health_check(self) -> bool:
        if not self.access_token:
            return False
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(
                    f"{self.API_BASE}/user/info/",
                    headers=self._headers(),
                    params={"fields": "open_id,display_name"},
                )
                data = resp.json()
                return data.get("error", {}).get("code") == "ok"
            except Exception:
                return False
