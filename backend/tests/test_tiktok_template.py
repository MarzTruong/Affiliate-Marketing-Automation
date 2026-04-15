"""Tests cho TIKTOK_SCRIPT_TEMPLATE và ReviewItemOut asset fields.

Kiểm tra:
1. Template có chứa đúng format bảng 4 dòng với timestamps parser cần
2. Output giả lập từ Claude được parse đúng bởi extract_voice_text + extract_script_parts
3. ReviewItemOut chấp nhận audio/heygen fields
"""

import pytest

from backend.ai_engine.prompts.templates import TIKTOK_SCRIPT_TEMPLATE
from backend.ai_engine.elevenlabs_engine import extract_voice_text
from backend.ai_engine.heygen_engine import extract_script_parts


# ── Fixtures ──────────────────────────────────────────────────────────────────

# Mô phỏng output mà Claude sẽ trả về từ TIKTOK_SCRIPT_TEMPLATE
SAMPLE_TIKTOK_OUTPUT = """| ⏱ Thời gian | 🎙 VOICE (Text-to-Speech) | 📹 VISUAL |
|-------------|--------------------------|-----------|
| 0–3s | *"3 giờ sáng mình pha sữa mà con khóc vì nguội quá"* | Cận cảnh đồng hồ 3:00 AM |
| 4–15s | *"Cái máy hâm này giữ 40°C liên tục 12 tiếng, mình không cần canh nữa"* | Close-up màn hình nhiệt độ |
| 16–35s | *"Hâm từ lạnh lên 37°C mất 3 phút thôi, con uống xong là ngủ lại ngay"* | Stop-motion hâm sữa |
| 36–45s | *"Dùng 1 tháng rồi, nhấn giỏ vàng góc trái nhé"* | Product shot + giỏ vàng |
"""


# ── Tests: TIKTOK_SCRIPT_TEMPLATE structure ───────────────────────────────────

def test_template_has_time_column():
    """Template hướng dẫn Claude output cột ⏱ Thời gian."""
    assert "⏱ Thời gian" in TIKTOK_SCRIPT_TEMPLATE


def test_template_has_voice_column():
    """Template hướng dẫn Claude output cột 🎙 VOICE."""
    assert "🎙 VOICE" in TIKTOK_SCRIPT_TEMPLATE


def test_template_has_visual_column():
    """Template hướng dẫn Claude output cột 📹 VISUAL."""
    assert "📹 VISUAL" in TIKTOK_SCRIPT_TEMPLATE


def test_template_has_hook_row():
    """Template có dòng timing 0–3s (hook)."""
    assert "0–3s" in TIKTOK_SCRIPT_TEMPLATE


def test_template_has_cta_row():
    """Template có dòng timing 36–45s (CTA)."""
    assert "36–45s" in TIKTOK_SCRIPT_TEMPLATE


def test_template_has_body_rows():
    """Template có 2 dòng body (4–15s và 16–35s)."""
    assert "4–15s" in TIKTOK_SCRIPT_TEMPLATE
    assert "16–35s" in TIKTOK_SCRIPT_TEMPLATE


def test_template_enforces_minh_pronoun():
    """Template yêu cầu dùng "mình" — KHÔNG dùng "tôi"."""
    assert '"mình"' in TIKTOK_SCRIPT_TEMPLATE
    assert "KHÔNG dùng" in TIKTOK_SCRIPT_TEMPLATE


def test_template_has_banned_words_rule():
    """Template liệt kê từ cấm."""
    assert "siêu phẩm" in TIKTOK_SCRIPT_TEMPLATE
    assert "hoàn hảo" in TIKTOK_SCRIPT_TEMPLATE


def test_template_has_gio_vang_cta():
    """Template yêu cầu CTA dùng 'giỏ vàng'."""
    assert "giỏ vàng" in TIKTOK_SCRIPT_TEMPLATE


def test_template_has_cot_placeholder():
    """Template chứa {{ cot_header }} placeholder."""
    assert "{{ cot_header }}" in TIKTOK_SCRIPT_TEMPLATE


def test_template_has_product_placeholders():
    """Template chứa đủ các placeholder sản phẩm."""
    for placeholder in ["{{ product_name }}", "{{ price }}", "{{ category }}", "{{ description }}"]:
        assert placeholder in TIKTOK_SCRIPT_TEMPLATE


def test_template_in_template_map():
    """TIKTOK_SCRIPT_TEMPLATE có trong TEMPLATE_MAP với key 'tiktok_script'."""
    from backend.ai_engine.content_generator import TEMPLATE_MAP
    assert "tiktok_script" in TEMPLATE_MAP
    assert TEMPLATE_MAP["tiktok_script"] is TIKTOK_SCRIPT_TEMPLATE


# ── Tests: extract_voice_text với TikTok output ───────────────────────────────

def test_extract_voice_text_gets_all_rows():
    """extract_voice_text trả về text từ cả 4 dòng (hook + 2 body + CTA)."""
    voice_text = extract_voice_text(SAMPLE_TIKTOK_OUTPUT)
    assert voice_text != ""
    assert "3 giờ sáng" in voice_text
    assert "40°C" in voice_text
    assert "37°C" in voice_text
    assert "giỏ vàng" in voice_text


def test_extract_voice_text_strips_asterisks():
    """extract_voice_text xóa dấu * khỏi output."""
    voice_text = extract_voice_text(SAMPLE_TIKTOK_OUTPUT)
    assert "*" not in voice_text


def test_extract_voice_text_skips_header():
    """extract_voice_text bỏ qua header row (🎙 VOICE)."""
    voice_text = extract_voice_text(SAMPLE_TIKTOK_OUTPUT)
    assert "🎙" not in voice_text
    assert "VOICE" not in voice_text.upper()


def test_extract_voice_text_not_empty():
    """extract_voice_text không trả về chuỗi rỗng với output hợp lệ."""
    voice_text = extract_voice_text(SAMPLE_TIKTOK_OUTPUT)
    assert len(voice_text) > 20


# ── Tests: extract_script_parts với TikTok output ────────────────────────────

def test_extract_hook_from_tiktok_output():
    """extract_script_parts lấy đúng hook text từ dòng 0–3s."""
    parts = extract_script_parts(SAMPLE_TIKTOK_OUTPUT)
    assert "3 giờ sáng" in parts.hook_text
    assert parts.hook_text != ""


def test_extract_cta_from_tiktok_output():
    """extract_script_parts lấy đúng CTA text từ dòng 36–45s."""
    parts = extract_script_parts(SAMPLE_TIKTOK_OUTPUT)
    assert "giỏ vàng" in parts.cta_text
    assert parts.cta_text != ""


def test_extract_body_not_in_hook_or_cta():
    """Body rows (4–35s) không xuất hiện trong hook hay CTA."""
    parts = extract_script_parts(SAMPLE_TIKTOK_OUTPUT)
    assert "12 tiếng" not in parts.hook_text
    assert "12 tiếng" not in parts.cta_text
    assert "3 phút" not in parts.hook_text
    assert "3 phút" not in parts.cta_text


def test_extract_empty_tiktok_script():
    """Output rỗng → cả 2 parts đều rỗng."""
    parts = extract_script_parts("")
    assert parts.hook_text == ""
    assert parts.cta_text == ""


# ── Tests: ReviewItemOut asset fields ────────────────────────────────────────

def test_review_item_out_has_asset_fields():
    """ReviewItemOut có 3 trường asset mới."""
    from backend.api.v1.automation import ReviewItemOut
    from datetime import datetime

    item = ReviewItemOut(
        post_id="abc",
        content_id="def",
        content_title="Test",
        content_body_preview="preview",
        content_type="tiktok_script",
        channel="tiktok",
        scheduled_at=datetime.now(),
        visual_url=None,
        rule_name=None,
        audio_url="http://localhost:8000/static/audio/test.mp3",
        heygen_hook_url="https://cdn.heygen.com/hook.mp4",
        heygen_cta_url="https://cdn.heygen.com/cta.mp4",
    )

    assert item.audio_url == "http://localhost:8000/static/audio/test.mp3"
    assert item.heygen_hook_url == "https://cdn.heygen.com/hook.mp4"
    assert item.heygen_cta_url == "https://cdn.heygen.com/cta.mp4"


def test_review_item_out_asset_fields_optional():
    """ReviewItemOut asset fields là optional — default None."""
    from backend.api.v1.automation import ReviewItemOut
    from datetime import datetime

    item = ReviewItemOut(
        post_id="abc",
        content_id="def",
        content_title=None,
        content_body_preview="",
        content_type="social_post",
        channel="facebook",
        scheduled_at=datetime.now(),
        visual_url=None,
        rule_name=None,
    )

    assert item.audio_url is None
    assert item.heygen_hook_url is None
    assert item.heygen_cta_url is None
