"""Tests cho Facebook Webhook Handler."""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def make_fb_signature(body: bytes, secret: str) -> str:
    """Tạo chữ ký HMAC-SHA256 giống Facebook."""
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


# ── Unit tests cho helper functions ─────────────────────────────────────────

class TestVerifySignature:
    def test_valid_signature(self):
        from backend.api.v1.webhooks import _verify_facebook_signature
        body = b'{"test": "data"}'
        secret = "my_secret"
        sig = make_fb_signature(body, secret)
        assert _verify_facebook_signature(body, sig, secret) is True

    def test_invalid_signature(self):
        from backend.api.v1.webhooks import _verify_facebook_signature
        body = b'{"test": "data"}'
        assert _verify_facebook_signature(body, "sha256=wrongdigest", "secret") is False

    def test_missing_signature(self):
        from backend.api.v1.webhooks import _verify_facebook_signature
        assert _verify_facebook_signature(b"data", None, "secret") is False

    def test_missing_secret_returns_false(self):
        from backend.api.v1.webhooks import _verify_facebook_signature
        assert _verify_facebook_signature(b"data", "sha256=abc", "") is False

    def test_wrong_prefix(self):
        from backend.api.v1.webhooks import _verify_facebook_signature
        assert _verify_facebook_signature(b"data", "sha1=abc", "secret") is False


class TestMapFbEventToMetrics:
    def test_reactions_map_to_clicks(self):
        from backend.api.v1.webhooks import _map_fb_event_to_metrics
        change = {"field": "reactions", "value": {"count": 42}}
        clicks, conversions, reach = _map_fb_event_to_metrics(change)
        assert clicks == 42
        assert conversions == 0
        assert reach == 0

    def test_likes_map_to_clicks(self):
        from backend.api.v1.webhooks import _map_fb_event_to_metrics
        change = {"field": "likes", "value": {"like_count": 10}}
        clicks, conversions, reach = _map_fb_event_to_metrics(change)
        assert clicks == 10

    def test_comments_map_to_clicks(self):
        from backend.api.v1.webhooks import _map_fb_event_to_metrics
        change = {"field": "comments", "value": {"comment_count": 5}}
        clicks, conversions, reach = _map_fb_event_to_metrics(change)
        assert clicks == 5

    def test_shares_map_to_conversions(self):
        from backend.api.v1.webhooks import _map_fb_event_to_metrics
        change = {"field": "shares", "value": {"share_count": 3}}
        clicks, conversions, reach = _map_fb_event_to_metrics(change)
        assert conversions == 3
        assert clicks == 0

    def test_reach_map_to_reach(self):
        from backend.api.v1.webhooks import _map_fb_event_to_metrics
        change = {"field": "reach", "value": {"count": 1000}}
        clicks, conversions, reach = _map_fb_event_to_metrics(change)
        assert reach == 1000

    def test_unknown_field_returns_zeros(self):
        from backend.api.v1.webhooks import _map_fb_event_to_metrics
        change = {"field": "unknown_event", "value": {}}
        assert _map_fb_event_to_metrics(change) == (0, 0, 0)


# ── Integration tests via HTTP ───────────────────────────────────────────────

class TestFacebookWebhookVerification:
    def test_verification_success(self, client):
        """GET /webhooks/facebook với token đúng → trả về challenge."""
        from backend.config import settings
        verify_token = settings.facebook_webhook_verify_token

        resp = client.get(
            "/api/v1/webhooks/facebook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": verify_token,
                "hub.challenge": "test_challenge_123",
            },
        )
        assert resp.status_code == 200
        assert resp.text == "test_challenge_123"

    def test_verification_wrong_token(self, client):
        """GET /webhooks/facebook với token sai → 403."""
        resp = client.get(
            "/api/v1/webhooks/facebook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "abc",
            },
        )
        assert resp.status_code == 403


class TestFacebookWebhookReceive:
    def _build_payload(self, external_post_id: str, field: str = "reactions", count: int = 5) -> dict:
        return {
            "object": "page",
            "entry": [{
                "id": "page_123",
                "changes": [{
                    "field": field,
                    "value": {"post_id": external_post_id, "count": count},
                }],
            }],
        }

    def test_receive_without_secret_no_signature_check(self, client):
        """POST khi chưa cấu hình webhook secret → không check signature."""
        payload = {"object": "page", "entry": []}
        resp = client.post(
            "/api/v1/webhooks/facebook",
            json=payload,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_receive_non_page_object_ignored(self, client):
        """POST với object != 'page' → ignored."""
        resp = client.post(
            "/api/v1/webhooks/facebook",
            json={"object": "user", "entry": []},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_receive_invalid_json(self, client):
        """POST với body không phải JSON → 400."""
        resp = client.post(
            "/api/v1/webhooks/facebook",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400

    def test_receive_with_invalid_signature_when_secret_set(self, client):
        """POST với sai chữ ký khi đã set secret → 401."""
        with patch("backend.api.v1.webhooks.settings") as mock_settings:
            mock_settings.facebook_webhook_secret = "real_secret"
            mock_settings.facebook_webhook_verify_token = "token"

            payload = self._build_payload("post_abc")
            body = json.dumps(payload).encode()
            resp = client.post(
                "/api/v1/webhooks/facebook",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": "sha256=invalidsignature",
                },
            )
        assert resp.status_code == 401

    def test_receive_skips_entry_without_post_id(self, client):
        """Entry không có post_id → skipped."""
        payload = {
            "object": "page",
            "entry": [{"changes": [{"field": "reactions", "value": {"count": 5}}]}],
        }
        resp = client.post("/api/v1/webhooks/facebook", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["processed"] == 0
        assert data["skipped"] >= 1

    @patch("backend.api.v1.webhooks.record_post_performance", new_callable=AsyncMock)
    def test_receive_calls_record_performance_when_post_found(self, mock_record):
        """Khi tìm thấy ScheduledPost khớp → gọi record_post_performance."""
        from backend.models.automation import ScheduledPost
        from backend.database import get_db
        from datetime import datetime, timezone
        from unittest.mock import MagicMock

        ext_id = f"fb_post_{uuid.uuid4().hex[:8]}"
        fake_post = MagicMock(spec=ScheduledPost)
        fake_post.id = uuid.uuid4()
        fake_post.external_post_id = ext_id

        # Mock DB session với dependency override
        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.return_value = fake_post
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_scalar)

        async def override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = override_get_db
        try:
            test_client = TestClient(app, raise_server_exceptions=False)
            payload = self._build_payload(ext_id, field="reactions", count=10)
            resp = test_client.post("/api/v1/webhooks/facebook", json=payload)
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args.kwargs
        assert call_kwargs["clicks"] == 10
