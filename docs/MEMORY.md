# MEMORY.md — Long-term Memory Bank

> Note: This file is autonomously updated by the AI to preserve context across sessions. Do not delete.

**Repo:** `MarzTruong/Affiliate-Marketing-Automation`
**Last updated:** 2026-04-20 (phiên 11 — OAuth fixed, 2-kênh strategy confirmed, affiliate creator API blocked by draft app)

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

- **[2026-04-16] SECURITY AUDIT — 3 P0 vulnerabilities fixed:** (1) `.env.prod` committed to GitHub với ANTHROPIC_API_KEY + POSTGRES_PASSWORD thật → scrubbed via `git filter-repo`. (2) `api.txt` trong git history chứa Claude + Gemini keys → scrubbed cùng `.env.prod`. (3) GitHub PAT `ghp_3KCT...` lộ trong `.git/config` remote URL → owner revoke thủ công, remote URL thay bằng clean HTTPS (Windows Credential Manager handle auth). Force push ghi đè `origin/main` từ e4001d4 → 9880fca.

- **[2026-04-16] `.gitignore` pattern upgrade:** Đổi từ `.env` + `.env.local` sang `.env.*` + `!.env.example` → chặn mọi biến thể `.env.prod/.env.dev/.env.staging`. Chỉ cho phép `.env.example` làm template.

- **[2026-04-13] OAuth callback DB key case mismatch:** TikTok OAuth callback lưu key lowercase (`tiktok_access_token`) nhưng `apply_db_settings()` tìm UPPERCASE (`TIKTOK_ACCESS_TOKEN`). Fix: chuẩn hóa lưu sang UPPERCASE trong callback.

- **[2026-04-13] TikTok `video_size: 0` rejected:** API TikTok từ chối payload khi `video_size = 0`. Fix: đặt `video_size: 1` để nhận `publish_id` và `upload_url` hợp lệ từ TikTok.

- **[2026-04-13] `social_post` content bị cắt giữa `<thinking>` tag:** Claude trả về CoT block chưa đóng tag khi `max_tokens` thấp. Fix: tăng `max_tokens` từ 500 → 1500 + `_strip_thinking_blocks()` xử lý unclosed tag.

- **[2026-04-13] AccessTrade price filter bỏ qua deals hợp lệ:** Deals từ AccessTrade có `price = 0` (coupon/deal, không phải sản phẩm giá 0). Fix: thêm `is_deal` flag, bỏ qua price/commission filter cho deals.

- **[2026-04-12] Prompt injection trong `FACEBOOK_PAGE_ID`:** Giá trị bị nhiễm `legitSECRET=injected`. Fix: validate + sanitize tất cả env vars khi load từ DB settings.

- **[2026-04-12] Settings page load `"****"` → user không sửa được:** Sensitive fields hiển thị masked value → khi save lại ghi `"****"` vào DB. Fix: load `""` (empty string) cho sensitive fields thay vì masked value.

---

## Architecture Decisions

- **[2026-04-20] Chiến lược 2 kênh đã xác nhận:** Kênh 1 "Lab Gia Dụng" = faceless automation, account marz.tiktok.affiliate01@gmail.com. Kênh 2 "Đồ Này Tui Xài" = semi-auto có xuất hiện thật, account kafekaykhe@gmail.com (đã có TikTok Shop + Partner Center). Cả 2 đều đã đăng ký TikTok Shop Affiliate Creator. CCCD chỉ đăng ký được 1 TikTok Shop → kafekaykhe là seller account, Lab Gia Dụng chỉ làm affiliate (không cần shop riêng).

- **[2026-04-20] TikTok Shop OAuth đúng spec — 4 fixes:** (1) Auth URL = `auth.tiktok-shops.com/oauth/authorize`, (2) param `app_key` không phải `client_key`, (3) token exchange dùng `auth_code` + `grant_type=authorized_code` + `app_secret`, (4) access token truyền qua header `x-tts-access-token` không phải query param. Signing = SHA256 plain (không phải HMAC-SHA256), path nằm trong signing string: `app_secret + path + sorted_params + app_secret`.

- **[2026-04-20] Affiliate Creator API blocked — nguyên nhân và next step:** `GET /affiliate_creator/202309/products/search` trả 404 vì Partner Center app "Affiliate Automation" đang ở trạng thái draft/pending approval. Trong khi chờ duyệt: cần lưu 2 token riêng (`TIKTOK_TOKEN_KENH1`, `TIKTOK_TOKEN_KENH2`) và build endpoint OAuth riêng cho từng kênh. Hiện tại chỉ có 1 token slot.

- **[2026-04-20] TikTok Shop Connector đã wire vào API:** `GET /api/v1/tiktok-shop/products/search?keyword=&limit=&min_commission=` đã có, dùng `get_connector()` factory từ DB settings. Sẵn sàng khi app được approve.

- **[2026-04-19] Phân tách nguồn sản phẩm theo kênh — QUAN TRỌNG:** TikTok (Kênh 1 + 2) dùng TikTok Shop Affiliate Creator API (`/affiliate_creator/202309/products/search`) — product tag trực tiếp trong video → viewer mua trên TikTok Shop → commission. AccessTrade CHỈ dùng cho Facebook/Instagram/YouTube (link affiliate ngoài). KHÔNG dùng AccessTrade làm source cho TikTok content. `backend/tiktok_shop/product_search.py` và `order_tracking.py` đã implement đúng, chỉ chưa wire vào pipeline TikTok. Affiliate Creator APIs hoạt động qua OAuth access token của tài khoản đã đăng ký Affiliate Creator — không cần bật trong "Manage API" panel của Partner Center.

- **[2026-04-19] TikTok Shop Partner Center app tạo thành công:** App "Affiliate Automation" (ID: 7629523665710335765), loại Dịch vụ tùy chỉnh, hạng mục Nhà phát triển nội bộ của người bán. Credentials đã có. 24 Seller APIs trong panel là để manage shop của seller — không liên quan đến Affiliate Creator APIs. App Key + App Secret đã có, cần thêm bước đăng ký TikTok Shop Affiliate Creator (qua app TikTok hoặc seller-vn.tiktok.com) để OAuth lấy được access token affiliate creator.

- **[2026-04-19] Phase 0 Foundation complete — TikTok dual-channel:** Kênh 1 (Faceless AI) dùng Gemini TTS (voice Aoede, giọng nữ miền Nam) + Kling AI (fal.ai, 3 clips 9:16x5s) + Hook A/B (Loop 4). Kênh 2 (Real Review) dùng ElevenLabs + HeyGen. `run_production(channel_type=)` dispatch đúng pipeline. Sub-niche: Mẹ bầu tiết kiệm + Đồ chơi Montessori.

- **[2026-04-19] ProductScore model field names:** `ctr`, `conversion`, `return_rate`, `orders_delta`, `score` — KHÔNG phải `actual_ctr`/`actual_conversion`/`total_orders` (tên cũ trong spec). Đã được fix khi merge Phase 0.

- **[2026-04-19] KlingEngine fal-client pattern:** fal-client không cài trong `.venv` → `__init__` check ImportError khi không có key. Tests dùng `KlingEngine.__new__()` để bypass import check. Smoke script kiểm tra `FAL_KEY` env var trước khi khởi tạo engine.

- **[2026-04-19] ProductScoringEngine là append-only (không upsert):** Mỗi lần `record_performance()` tạo 1 row mới (insert). `top_products()` dùng subquery `GROUP BY product_id MAX(score)` để tránh trả nhiều row cùng product. Metric validation: `ctr/conversion/return_rate` phải trong `[0.0, 1.0]`, `orders_delta >= 0`.

- **[2026-04-19] Alembic migration Phase 0 chưa apply:** File `f6a7b8c9d0e1_add_tiktok_phase0_tables.py` tạo bằng tay (Docker offline). Cần `alembic upgrade head` khi Docker chạy để tạo `hook_variants`, `product_scores`, `tag_queue_items`.

- **[2026-04-19] Tag Queue flow:** Video xong → enqueue vào `tag_queue_items` → Owner mở `/tag-queue` frontend → click "Đánh dấu đã tag" → click "Đã publish". Không có TikTok API cho tag automation → owner thao tác thủ công trên TikTok Studio app.

- **[2026-04-16] Pipeline Fail Loud pattern — non-critical per-item failures:** Visual + content generation lỗi 1 sản phẩm không nên kill toàn pipeline (sản phẩm khác vẫn chạy). Pattern: `try/except` với `logger.error(exc_info=True)` + increment counter (`visual_failures`, `content_failures`) + expose vào `run_details`. Cảnh báo thêm nếu `content_failures > 0 and content_created == 0`. KHÔNG `raise` per-item nhưng vẫn fail loud qua log + metric.

- **[2026-04-16] Fail Loud PostToolUse hook pattern:** `scripts/check_fail_loud.py` đọc tool_input JSON từ stdin, quét `.py` trong `backend/` cho pattern `except.*: pass|return None|return`. Warn qua stderr, không block (exit 0) để tránh false positive phá workflow. Đăng ký trong `.claude/settings.local.json` qua PostToolUse matcher `Edit|Write`.

- **[2026-04-16] Docker Compose dev bind 127.0.0.1:** Bind explicit `127.0.0.1:5432:5432` và `127.0.0.1:6379:6379` thay vì default `5432:5432` (bind `0.0.0.0`). Tránh expose Postgres/Redis ra mạng local/VPN. Production dùng docker network internal (không expose port).

- **[2026-04-16] Git history rewrite protocol:** Khi cần xóa secret/file khỏi git history: (1) backup bằng `git bundle create --all`, (2) stash pending work, (3) dùng `git-filter-repo --invert-paths --path FILE --force` (Python package, cài qua `.venv/Scripts/pip install git-filter-repo`), (4) re-add origin với URL sạch (không token), (5) `git stash pop`, (6) commit fixes, (7) `git push --force origin main`. Filter-repo tự strip remote để tránh accidental push — phải re-add. Cần owner confirm `TÔI XÁC NHẬN XÓA LỊCH SỬ`.

- **[2026-04-16] HeyGen async polling pattern:** HeyGen render video bất đồng bộ (~1-3 phút). Pattern: submit job → nhận video_id → poll GET /v1/video/{id} mỗi 10s → completed/failed. Timeout mặc định 600s. 2 clips (hook + CTA) submit và poll song song bằng asyncio.gather.
- **[2026-04-14] ElevenLabs VoiceSettings import ở module level:** Import `VoiceSettings` và `AsyncElevenLabs` bằng try/except ở module level (không phải bên trong method) để unit test có thể patch được bằng `patch("backend.ai_engine.elevenlabs_engine.VoiceSettings")`.
- **[2026-04-16] Cách đề xuất phương án kỹ thuật:** Luôn dùng bảng cụ thể (file nào đổi, dòng nào sửa) thay vì giải thích chung chung — owner cần thông tin cụ thể để ra quyết định, không phải lý thuyết.

- **[2026-04-16] Secrets KHÔNG BAO GIỜ commit dưới bất kỳ hình thức nào:** Kể cả `.env.prod`, `api.txt`, comment tạm thời. Mọi API key (Claude, Gemini, GitHub PAT, platform tokens) phải ở (a) `.env` gitignored hoặc (b) DB table `system_settings`. Quy trình rotate khẩn cấp: revoke ngay trên provider console TRƯỚC khi rewrite git history (bot scan GitHub có thể đã cache key).

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
