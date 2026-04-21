"""Tests for Kling image resolution & auto-upscale logic.

Covers _resolve_kling_image and _upscale_and_upload in tiktok/production.py:
- Ảnh ≥300x300 → dùng URL gốc
- Ảnh <300x300 → upscale Pillow LANCZOS → upload fal.ai CDN
- Download/upscale fail → fallback URL gốc
"""
from __future__ import annotations

from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image

from backend.tiktok.production import _resolve_kling_image, _upscale_and_upload


def _make_image_bytes(width: int, height: int, fmt: str = "JPEG") -> bytes:
    img = Image.new("RGB", (width, height), color=(200, 100, 50))
    buf = BytesIO()
    img.save(buf, format=fmt, quality=90)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upscale_small_image_reaches_512():
    """260x260 phải được upscale lên ≥512px cạnh ngắn."""
    small_data = _make_image_bytes(260, 260)

    with patch("fal_client.upload", return_value="https://fal.ai/cdn/upscaled.jpg") as mock_upload:
        url = await _upscale_and_upload(small_data, "https://orig.com/tiny.jpg", "Test Product")

    assert url == "https://fal.ai/cdn/upscaled.jpg"
    assert mock_upload.called
    uploaded_bytes, content_type = mock_upload.call_args.args
    assert content_type == "image/jpeg"

    # Verify upscaled size
    upscaled = Image.open(BytesIO(uploaded_bytes))
    assert min(upscaled.size) >= 512, f"cạnh ngắn nhất phải ≥512, got {upscaled.size}"


@pytest.mark.asyncio
async def test_upscale_preserves_aspect_ratio():
    """Ảnh 200x260 phải giữ tỷ lệ khi upscale."""
    data = _make_image_bytes(200, 260)

    with patch("fal_client.upload", return_value="https://fal.ai/cdn/x.jpg") as mock_upload:
        await _upscale_and_upload(data, "https://orig.com/x.jpg", "Test")

    uploaded_bytes = mock_upload.call_args.args[0]
    upscaled = Image.open(BytesIO(uploaded_bytes))
    # Cạnh ngắn (200) phải scale lên 512 → tỷ lệ 2.56x → 200*2.56=512, 260*2.56=665
    assert upscaled.size[0] == 512
    assert upscaled.size[1] > 600


@pytest.mark.asyncio
async def test_upscale_upload_fail_returns_none():
    """Upload fail → trả None, không raise (caller tự fallback)."""
    data = _make_image_bytes(260, 260)

    with patch("fal_client.upload", side_effect=RuntimeError("fal.ai down")):
        url = await _upscale_and_upload(data, "https://orig.com/x.jpg", "Test")

    assert url is None


@pytest.mark.asyncio
async def test_resolve_kling_image_large_returns_original():
    """Ảnh 500x500 (≥300) phải trả URL gốc, không upscale."""
    big_data = _make_image_bytes(500, 500)

    mock_resp = AsyncMock()
    mock_resp.content = big_data
    mock_resp.headers = {"content-type": "image/jpeg"}
    mock_resp.raise_for_status = lambda: None

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        url = await _resolve_kling_image("https://tiktok.com/big.jpg", "Test")

    assert url == "https://tiktok.com/big.jpg"


@pytest.mark.asyncio
async def test_resolve_kling_image_small_triggers_upscale():
    """Ảnh 260x260 (<300) phải gọi upscale+upload và trả URL mới."""
    small_data = _make_image_bytes(260, 260)

    mock_resp = AsyncMock()
    mock_resp.content = small_data
    mock_resp.headers = {"content-type": "image/jpeg"}
    mock_resp.raise_for_status = lambda: None

    with patch("httpx.AsyncClient") as mock_client, \
         patch("backend.tiktok.production._upscale_and_upload", AsyncMock(return_value="https://fal.ai/cdn/upscaled.jpg")) as mock_up:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        url = await _resolve_kling_image("https://tiktok.com/tiny.jpg", "Test Product")

    assert url == "https://fal.ai/cdn/upscaled.jpg"
    mock_up.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_kling_image_upscale_fail_returns_original():
    """Upscale fail → trả URL gốc (fal.ai có thể reject, nhưng không crash pipeline)."""
    small_data = _make_image_bytes(260, 260)

    mock_resp = AsyncMock()
    mock_resp.content = small_data
    mock_resp.headers = {"content-type": "image/jpeg"}
    mock_resp.raise_for_status = lambda: None

    with patch("httpx.AsyncClient") as mock_client, \
         patch("backend.tiktok.production._upscale_and_upload", AsyncMock(return_value=None)):
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        url = await _resolve_kling_image("https://tiktok.com/tiny.jpg", "Test")

    assert url == "https://tiktok.com/tiny.jpg"


@pytest.mark.asyncio
async def test_resolve_kling_image_non_image_content_type_returns_none():
    """URL trả HTML không phải ảnh → trả None."""
    mock_resp = AsyncMock()
    mock_resp.content = b"<html></html>"
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.raise_for_status = lambda: None

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        url = await _resolve_kling_image("https://example.com/page", "Test")

    assert url is None
