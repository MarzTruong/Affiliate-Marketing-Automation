# MEMORY.md — Long-term Memory Bank

> Note: This file is autonomously updated by the AI to preserve context across sessions. Do not delete.

**Repo:** `MarzTruong/Affiliate-Marketing-Automation`
**Last updated:** 2026-04-16 (phiên 6)

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

- **[2026-04-14] HeyGen async polling pattern:** HeyGen render video bất đồng bộ (~1-3 phút). Pattern: submit job → nhận video_id → poll GET /v1/video/{id} mỗi 10s → completed/failed. Timeout mặc định 600s. 2 clips (hook + CTA) submit và poll song song bằng asyncio.gather.
- **[2026-04-14] ElevenLabs VoiceSettings import ở module level:** Import `VoiceSettings` và `AsyncElevenLabs` bằng try/except ở module level (không phải bên trong method) để unit test có thể patch được bằng `patch("backend.ai_engine.elevenlabs_engine.VoiceSettings")`.
- **[2026-04-16] Cách đề xuất phương án kỹ thuật:** Luôn dùng bảng cụ thể (file nào đổi, dòng nào sửa) thay vì giải thích chung chung — owner cần thông tin cụ thể để ra quyết định, không phải lý thuyết.

- **[2026-04-16] SQLAlchemy `mapped_column(default=...)` chỉ áp dụng khi INSERT:** `default=` trong `mapped_column` không set giá trị ở Python object level khi `__init__`. Phải truyền tường minh hoặc dùng `server_default` (DB-level). Tests nên tránh assert Python-level defaults nếu không truyền vào constructor.

- **[2026-04-16] Backend module split — backward-compat shims:** Khi move package (`backend/connectors/` → `backend/affiliate/connectors/`), giữ `__init__.py` cũ làm shim re-export từ path mới. Tránh break code cũ còn import từ path gốc (analytics, workers, tests).

- **[2026-04-14] TikTok channel strategy — content only, no direct affiliate links:** TikTok = kênh nội dung (faceless review video) + "link in bio". Facebook = kênh affiliate link trực tiếp. Không đặt link TMĐT trong caption TikTok.
- **[2026-04-14] Không dùng Make/n8n:** Hệ thống đã có APScheduler + custom pipeline + webhook — thêm Make/n8n tạo ra 2 layer chồng chéo không cần thiết. Quyết định: giữ custom backend, mở rộng bằng cách thêm engine mới (ElevenLabs, HeyGen) theo pattern `GeminiEngine`.

- **[2026-04-14] TikTok strategy: Content channel, NOT affiliate link channel:** TikTok nghiêm ngặt về link affiliate từ sàn TMĐT ngoài. Quyết định: TikTok = kênh nội dung (faceless review video) → CTA về "link in bio" → landing page. Facebook = kênh phân phối affiliate link trực tiếp.

- **[2026-04-14] Content workflow TikTok = Hybrid (Auto + Manual):** Script + ElevenLabs audio + HeyGen clips = tự động. B-roll quay + CapCut dựng = thủ công (không thể tự động hóa). Hệ thống notify qua Telegram khi assets sẵn sàng để owner thao tác tiếp.

- **[2026-04-16] TikTok Studio module split (backend):** `backend/tiktok/` = TikTok Studio (production pipeline, CRUD, router). `backend/affiliate/` = Affiliate automation (pipeline, scheduler, connectors, publishers). Shared: `ai_engine/`, `analytics/`, `models/`, `api/v1/` URLs không đổi. Old paths (`backend/connectors/`, `backend/publisher/`) giữ làm shims.

- **[2026-04-13] AccessTrade là primary data source:** Shopee unofficial scraping đã bị xóa (vi phạm ToS). AccessTrade là connector duy nhất cho tất cả platform search (Shopee, Tiki, Lazada).

- **[2026-04-12] Credentials lưu DB, không lưu `.env`:** Tất cả platform API keys lưu vào bảng `system_settings`, quản lý qua UI `/settings`. Chỉ `DATABASE_URL`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` được phép ở `.env`.

- **[2026-04-12] Migration Alembic — không sửa migration đã apply:** Khi cần thay đổi schema, tạo migration mới (`alembic revision --autogenerate`). Tuyệt đối không edit file migration cũ đã chạy.

- **[2026-04-11] AI System Prompt Hierarchy:** `BASE_SYSTEM` (hướng dẫn chung) + `TASK_CONTEXT` (per content_type) + `FEW_SHOT examples` (từ `AITrainingData`). Cache ephemeral để giảm token cost.

- **[2026-04-11] Human-in-the-Loop là bắt buộc:** Tất cả AI-generated content phải qua Review Queue (status `pending_review`) trước khi publish. Approve → lưu `AITrainingData` với signal `approved`. Edit rồi approve → `edited_then_approved`.
