"""Tests cho send_tiktok_ready_to_post — Plan D' Hybrid Telegram notify."""
from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_send_ready_to_post_sends_video(tmp_path):
    """File tồn tại → gọi _send_video với đúng tham số."""
    video_file = tmp_path / "test.mp4"
    video_file.write_bytes(b"\x00" * 1024)

    with patch("backend.reports.telegram_reporter._send_video", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        with patch("backend.reports.telegram_reporter.settings") as mock_settings:
            mock_settings.telegram_bot_token = "test_token"
            mock_settings.telegram_channel_id = "test_chat"

            from backend.reports.telegram_reporter import send_tiktok_ready_to_post

            await send_tiktok_ready_to_post(
                project_id=str(uuid.uuid4()),
                product_name="Nồi Áp Suất",
                video_path=str(video_file),
                caption_text="Caption test TikTok #product",
                affiliate_url="https://shopee.vn/xxx",
                duration_s=15.5,
            )

    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args
    assert call_kwargs[0][0] == video_file.read_bytes()  # video_bytes
    assert call_kwargs[0][1].endswith(".mp4")            # filename is mp4
    assert "tiktok_" in call_kwargs[0][1].lower()        # filename has tiktok_ prefix
    caption_arg = call_kwargs[0][2]
    assert "Nồi Áp Suất" in caption_arg
    assert "Caption test TikTok" in caption_arg
    assert "shopee.vn" in caption_arg


@pytest.mark.asyncio
async def test_send_ready_to_post_missing_file_sends_text_fallback():
    """File không tồn tại → gửi text fallback thay vì crash."""
    with patch("backend.reports.telegram_reporter._send", new_callable=AsyncMock) as mock_text:
        with patch("backend.reports.telegram_reporter.settings") as mock_settings:
            mock_settings.telegram_bot_token = "tok"
            mock_settings.telegram_channel_id = "chat"

            from backend.reports.telegram_reporter import send_tiktok_ready_to_post

            await send_tiktok_ready_to_post(
                project_id="abc123",
                product_name="Test Product",
                video_path="/nonexistent/video.mp4",
                caption_text="Caption",
            )

    mock_text.assert_called_once()
    assert "abc123" in mock_text.call_args[0][0]


@pytest.mark.asyncio
async def test_send_ready_to_post_video_upload_fails_sends_fallback(tmp_path):
    """_send_video trả False → fallback _send text."""
    video_file = tmp_path / "v.mp4"
    video_file.write_bytes(b"\x00" * 512)

    with patch("backend.reports.telegram_reporter._send_video", new_callable=AsyncMock, return_value=False), \
         patch("backend.reports.telegram_reporter._send", new_callable=AsyncMock) as mock_text, \
         patch("backend.reports.telegram_reporter.settings") as mock_settings:
        mock_settings.telegram_bot_token = "tok"
        mock_settings.telegram_channel_id = "chat"

        from backend.reports.telegram_reporter import send_tiktok_ready_to_post

        await send_tiktok_ready_to_post(
            project_id="proj1",
            product_name="Máy Lọc Nước",
            video_path=str(video_file),
            caption_text="cap",
        )

    mock_text.assert_called_once()
    assert "Máy Lọc Nước" in mock_text.call_args[0][0]


@pytest.mark.asyncio
async def test_send_ready_to_post_no_affiliate_url(tmp_path):
    """Không có affiliate_url → caption không chứa link affiliate."""
    video_file = tmp_path / "v.mp4"
    video_file.write_bytes(b"\x00" * 512)

    with patch("backend.reports.telegram_reporter._send_video", new_callable=AsyncMock) as mock_send, \
         patch("backend.reports.telegram_reporter.settings") as mock_settings:
        mock_send.return_value = True
        mock_settings.telegram_bot_token = "tok"
        mock_settings.telegram_channel_id = "chat"

        from backend.reports.telegram_reporter import send_tiktok_ready_to_post

        await send_tiktok_ready_to_post(
            project_id="proj2",
            product_name="Sản Phẩm Test",
            video_path=str(video_file),
            caption_text="caption no url",
            affiliate_url=None,
        )

    caption = mock_send.call_args[0][2]
    assert "href" not in caption
    assert "Link affiliate" not in caption
