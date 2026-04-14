# MEMORY.md — Long-term Memory Bank

> Note: This file is autonomously updated by the AI to preserve context across sessions. Do not delete.

**Repo:** `MarzTruong/Affiliate-Marketing-Automation`
**Last updated:** 2026-04-14

---

## Quirks & Custom Rules

- **Đại từ TikTok scripts:** Luôn dùng "mình" — không dùng "tôi", "bạn", "chúng ta".
- **Từ cấm trong content:** `siêu phẩm`, `hoàn hảo`, `tuyệt vời`, `số 1`, `tốt nhất`, `không thể thiếu`.
- **ECC path (Windows):** Plugin Claude Code đặt tại `E:\.claude\.claude` — không phải `C:\Users\Marz\.claude`.
- **Gemini SDK:** Dùng `google-genai` (v1.70.0+) — KHÔNG dùng `google-generativeai` (deprecated).
- **Gemini model:** `gemini-2.0-flash` — đã downgrade từ `gemini-2.5-pro` do quota tier thấp hơn.
- **Venv path:** `.venv/` ở root project — không phải trong `backend/`.
- **DB settings case:** `apply_db_settings()` đọc key UPPERCASE — lưu lowercase sẽ không load được.
- **TikTok token:** Hết hạn sau 24h (sandbox). Cần re-auth qua `/auth/tiktok` mỗi ngày khi dùng sandbox.
- **Facebook Webhook secret:** Để trống `FACEBOOK_WEBHOOK_SECRET` nếu chưa set — hệ thống skip verify.
- **PDF Report:** Dùng `fpdf2` với ASCII-safe text — không dùng font Unicode để tránh encoding lỗi.
- **TikTok affiliate links:** KHÔNG đặt link affiliate sàn TMĐT trực tiếp trong caption TikTok — dùng "link in bio" → landing page.

---

## Resolved Edge Cases

- **[2026-04-13] OAuth callback DB key case mismatch:** TikTok OAuth callback lưu key lowercase (`tiktok_access_token`) nhưng `apply_db_settings()` tìm UPPERCASE (`TIKTOK_ACCESS_TOKEN`). Fix: chuẩn hóa lưu sang UPPERCASE trong callback.

- **[2026-04-13] TikTok `video_size: 0` rejected:** API TikTok từ chối payload khi `video_size = 0`. Fix: đặt `video_size: 1` để nhận `publish_id` và `upload_url` hợp lệ từ TikTok.

- **[2026-04-13] `social_post` content bị cắt giữa `<thinking>` tag:** Claude trả về CoT block chưa đóng tag khi `max_tokens` thấp. Fix: tăng `max_tokens` từ 500 → 1500 + `_strip_thinking_blocks()` xử lý unclosed tag.

- **[2026-04-13] AccessTrade price filter bỏ qua deals hợp lệ:** Deals từ AccessTrade có `price = 0` (coupon/deal, không phải sản phẩm giá 0). Fix: thêm `is_deal` flag, bỏ qua price/commission filter cho deals.

- **[2026-04-12] Prompt injection trong `FACEBOOK_PAGE_ID`:** Giá trị bị nhiễm `legitSECRET=injected`. Fix: validate + sanitize tất cả env vars khi load từ DB settings.

- **[2026-04-12] Settings page load `"****"` → user không sửa được:** Sensitive fields hiển thị masked value → khi save lại ghi `"****"` vào DB. Fix: load `""` (empty string) cho sensitive fields thay vì masked value.

---

## Architecture Decisions

- **[2026-04-14] Không dùng Make/n8n:** Hệ thống đã có APScheduler + custom pipeline + webhook — thêm Make/n8n tạo ra 2 layer chồng chéo không cần thiết. Quyết định: giữ custom backend, mở rộng bằng cách thêm engine mới (ElevenLabs, HeyGen) theo pattern `GeminiEngine`.

- **[2026-04-14] TikTok strategy: Content channel, NOT affiliate link channel:** TikTok nghiêm ngặt về link affiliate từ sàn TMĐT ngoài. Quyết định: TikTok = kênh nội dung (faceless review video) → CTA về "link in bio" → landing page. Facebook = kênh phân phối affiliate link trực tiếp.

- **[2026-04-14] Content workflow TikTok = Hybrid (Auto + Manual):** Script + ElevenLabs audio + HeyGen clips = tự động. B-roll quay + CapCut dựng = thủ công (không thể tự động hóa). Hệ thống notify qua Telegram khi assets sẵn sàng để owner thao tác tiếp.

- **[2026-04-13] AccessTrade là primary data source:** Shopee unofficial scraping đã bị xóa (vi phạm ToS). AccessTrade là connector duy nhất cho tất cả platform search (Shopee, Tiki, Lazada).

- **[2026-04-12] Credentials lưu DB, không lưu `.env`:** Tất cả platform API keys lưu vào bảng `system_settings`, quản lý qua UI `/settings`. Chỉ `DATABASE_URL`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` được phép ở `.env`.

- **[2026-04-12] Migration Alembic — không sửa migration đã apply:** Khi cần thay đổi schema, tạo migration mới (`alembic revision --autogenerate`). Tuyệt đối không edit file migration cũ đã chạy.

- **[2026-04-11] AI System Prompt Hierarchy:** `BASE_SYSTEM` (hướng dẫn chung) + `TASK_CONTEXT` (per content_type) + `FEW_SHOT examples` (từ `AITrainingData`). Cache ephemeral để giảm token cost.

- **[2026-04-11] Human-in-the-Loop là bắt buộc:** Tất cả AI-generated content phải qua Review Queue (status `pending_review`) trước khi publish. Approve → lưu `AITrainingData` với signal `approved`. Edit rồi approve → `edited_then_approved`.
