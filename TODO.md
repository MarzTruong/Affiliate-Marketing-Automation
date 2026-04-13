# TODO — Affiliate Marketing Automation

> Cập nhật lần cuối: 13/04/2026 (phiên 3)

---

## Hoàn thành (08–12/04/2026)

### Server & Môi trường
- [x] Dừng Docker cũ, chuyển sang chạy dev server trực tiếp từ source
- [x] Kill process trùng lặp trên port 8000 → còn đúng 1
- [x] Xác nhận cấu trúc đúng: Frontend :3000 → Backend :8000 → PostgreSQL :5432 (Docker)
- [x] Fix đường dẫn plugin ECC: toàn bộ `C:\Users\Marz\.claude` → `E:\.claude\.claude`

### Tính năng mới (Phase 1)
- [x] **Automation Rules** — tạo rule tự động quét SP, lọc theo tiêu chí, AI content, lên lịch
- [x] **Adaptive Scheduler** — tự học giờ đăng tốt nhất bằng EMA + epsilon-greedy
- [x] **Content Calendar** — xem lịch đăng bài theo tuần, phân nhóm theo kênh
- [x] **AI Chat (CBD)** — điều khiển hệ thống bằng hội thoại tiếng Việt (Claude API)
- [x] **Visual Generator** — Bannerbear API + Pillow fallback tạo ảnh tự động
- [x] **Review Queue** — pipeline tạo `pending_review`, user approve/reject từng bài
- [x] **Bulk Approve/Reject** — checkbox select + bulk action bar trong Review Queue UI

### Bảo mật & Kiến trúc
- [x] **[CRITICAL] Vá lỗi ghi đè `.env` qua API** — credentials lưu vào DB `system_settings`
- [x] **[HIGH] Setup Alembic Migration** — baseline `967ba0427f3c`, migration `ffc02157caee`
- [x] **[CRITICAL] Xóa Shopee unofficial scraping** — delegate sang AccessTrade
- [x] **[HIGH] Rate Limiter & Exponential Backoff** — Tenacity + RateLimiter 0.5s
- [x] **Xóa prompt injection** — `FACEBOOK_PAGE_ID` bị nhiễm `legitSECRET=injected`, đã clear

### AI Engine Upgrades
- [x] **System Prompt Hierarchy** — `BASE_SYSTEM` + `TASK_CONTEXT` per content type, cache ephemeral
- [x] **Chain-of-Thought (CoT)** — 3-step `<thinking>` block inject vào prompt
- [x] **Few-Shot Learning** — `AITrainingData` table, load examples theo category/content_type
- [x] **Human-in-the-Loop Feedback** — approve → lưu AITrainingData; edited → `edited_then_approved`
- [x] **Strip CoT blocks** — `_strip_thinking_blocks()` xóa `<thinking>...</thinking>` trước khi lưu DB
- [x] **Gemini Vision Engine** — `google-genai` SDK (v1.70.0), model `gemini-2.5-pro`
  - `analyze_product_image()` với httpx async download + thread pool call
  - Error handling: `GeminiRateLimitError`, `GeminiAuthError`, `GeminiTimeoutError`
  - `create_gemini_engine()` factory, init trong app lifespan
- [x] **Gemini wired vào pipeline** — `ContentGenerator` lazy-init Gemini, enrich description từ ảnh trước khi gọi Claude
- [x] **pipeline.py lưu `image_urls`** — list URLs vào `metadata_json` để Gemini đọc được

### Git & Hệ thống
- [x] **Khởi tạo Git repo** — push lên GitHub `MarzTruong/Affiliate-Marketing-Automation`
- [x] **CLAUDE.md refactor** — English, modular, BMAD approach (docs/ARCHITECTURE.md + docs/WORKFLOW.md)

### Phase 2 — Hoàn thành
- [x] **Bug Fix: Calendar** — thêm filter tabs (Tất cả / Chờ duyệt / Đã lên lịch / Đã đăng / Thất bại), badge đếm pending
- [x] **Bug Fix: Review Queue** — tăng preview 200 → 500 ký tự + nút "Xem đầy đủ" toggle
- [x] **Webhook Facebook** — `POST /webhooks/facebook`: verify HMAC-SHA256, parse engagement → `record_post_performance()`. 19 tests passing.
- [x] **PDF Weekly Report** — `generate_weekly_pdf()` + `send_weekly_pdf_report()` qua Telegram `sendDocument`. Scheduled thứ 2 07:05 VN.

### Kiểm thử thực tế
- [x] Pipeline end-to-end chạy thành công (mock data): scan → filter → Claude content → pending_review
- [x] Approve/Reject flow hoạt động: AITrainingData được lưu đúng signal
- [x] Bulk approve/reject: `{"approved": 3, "total": 3}` và HTTP 204
- [x] Gemini được gọi trong pipeline: log `[GeminiEngine]` xuất hiện, graceful fallback khi lỗi download

---

## Lỗi / Hạn chế còn tồn đọng

| # | Mức độ | Vấn đề | Ghi chú |
|---|--------|--------|---------|
| 1 | INFO | TikTok chỉ hỗ trợ draft mode | Giới hạn của TikTok Content API |
| 2 | INFO | Gemini mock image URLs (placeholder.com) bị block | Sẽ tự resolve khi có ảnh thật từ AccessTrade |
| 3 | PRE-EXISTING | 3 test failures trong test_publisher.py + test_sop_engine.py | Không liên quan Phase 2, cần fix riêng |

---

## Bước tiếp theo (Phase 3)

### Ưu tiên cao
- [ ] **Facebook Publisher** — chờ thiết bị được tin tưởng (vài ngày) → tạo Meta Developer → lấy Page Token → test đăng bài thật
- [x] **TikTok OAuth flow** — HOÀN THÀNH: OAuth sandbox, token lưu DB, `/auth/tiktok/me`, `/publisher/health`, publish draft thành công
- [ ] **TikTok video upload** — để post thật cần upload video MP4 vào `upload_url`. Cân nhắc tạo slide video từ ảnh sản phẩm.

### Ưu tiên trung bình
- [ ] **Multi-account support** — nhiều Facebook Page, nhiều WordPress site (phức tạp: DB migration + UI + publisher routing)
- [ ] **Gemini Vision test thật** — quota reset hàng ngày, test với ảnh thật Shopee/Tiki

### Hoàn thành trong phiên 4 (13-14/04/2026)
- [x] **TikTok Sandbox setup** — App Key/Secret, Redirect URI, Direct Post ON, scopes (user.info.basic + video.publish + video.upload)
- [x] **TikTok OAuth 2.0 hoàn chỉnh** — `/auth/tiktok` → TikTok → `/auth/tiktok/callback` → token lưu DB
- [x] **Fix bug DB key case** — OAuth callback lưu lowercase, `apply_db_settings()` tìm uppercase → đã fix sang UPPERCASE
- [x] **`GET /auth/tiktok/me`** — test token + lấy user info (open_id, display_name)
- [x] **`GET /publisher/health`** — check tất cả platforms, TikTok: ok, Telegram: ok
- [x] **TikTok publisher fix** — `video_size: 0` → `1` để TikTok trả publish_id + upload_url hợp lệ
- [x] **Publish end-to-end** — `POST /publisher/publish` → TikTok → `status: published`, `publish_id` thật từ TikTok API

### Ghi chú cho phiên tiếp theo
> **TikTok giới hạn:** API chỉ nhận VIDEO, không có text-only post. Draft hiện tại có `publish_id` và `upload_url` hợp lệ từ TikTok. Để post thật cần upload file video MP4 vào `upload_url` đó. Hướng đi: tạo slide video từ ảnh sản phẩm (ffmpeg hoặc moviepy).
>
> **Ngrok:** Token TikTok hết hạn sau 24h. Cần re-auth qua `/auth/tiktok` mỗi ngày khi dùng sandbox. Khi production sẽ có refresh_token.
>
> **Bước tiếp theo ưu tiên:**
> 1. TikTok video: tạo slide MP4 từ ảnh sản phẩm → upload vào `upload_url` → post thật
> 2. Facebook Publisher: nếu thiết bị đã được trust → tạo Meta Developer App → lấy Page Token

### Hoàn thành trong phiên 3 (13/04/2026)
- [x] **Fix 3 pre-existing test failures** — test_publisher_registry, test_get_publisher_unknown, test_pick_variant_balanced → 78/78 passed
- [x] **AccessTrade connector rewrite** — auth endpoint `/transactions`, mapping deals/coupons (price=0, aff_link, coupon codes)
- [x] **Pipeline filter fix** — bỏ qua price/commission filter cho deals (is_deal check)
- [x] **social_post max_tokens** — 500 → 1500, _strip_thinking_blocks() xử lý unclosed `<thinking>` tag
- [x] **Settings page fix** — sensitive fields load `""` thay vì `"****"` để user gõ được
- [x] **Gemini model downgrade** — `gemini-2.5-pro` → `gemini-2.0-flash` (quota tier thấp hơn)
- [x] **Pipeline end-to-end thật** — AccessTrade Shopee → 50 deals → 5 lọc → 5 bài Claude Vietnamese → scheduled

### Ưu tiên thấp
- [ ] Sync/cập nhật ECC skills & agents (hiện có 57 skills, 47 agents)

---

## Cách khởi động lại hệ thống

```bash
# 1. Khởi động PostgreSQL + Redis (Docker)
docker-compose up -d postgres redis

# 2. Kill server cũ nếu còn (Windows)
powershell.exe -Command "Get-Process python | Stop-Process -Force"

# 3. Khởi động Backend (từ thư mục root project)
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Frontend
cd frontend && npm run dev
```

**Kiểm tra nhanh:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/v1/automation
- Backend docs: http://localhost:8000/docs

---

## Ghi chú kỹ thuật

- **Database**: PostgreSQL qua Docker (`affiliate_postgres`), Alembic migration đã setup
- **Credentials**: Platform API keys lưu trong bảng `system_settings` — quản lý qua UI `/settings`
- **Chỉ trong `.env`**: `DATABASE_URL`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`
- **Connectors**: AccessTrade là primary source cho tất cả platform search. Rate limit 0.5s + Tenacity retry
- **Gemini SDK**: Dùng `google-genai` (v1.70.0+) — **không** dùng `google-generativeai` (deprecated)
- **Gemini models**: `gemini-2.0-flash` (vision + text) — đã đổi từ 2.5-pro do quota
- **CoT blocks**: Claude trả về `<thinking>...</thinking>` trong output — bị strip bởi `_strip_thinking_blocks()` trước khi lưu DB
- **Venv**: `.venv/` ở root project (không phải trong `backend/`)
- **Log**: `backend.log` và `backend_err.log` ở root project
- **Server rule**: Luôn chạy 1 server duy nhất mỗi port
- **Kill server (Windows)**: `powershell.exe -Command "Get-Process python | Stop-Process -Force"`
- **Webhook Facebook**: `FACEBOOK_WEBHOOK_VERIFY_TOKEN=affiliate_webhook_verify` (default), `FACEBOOK_WEBHOOK_SECRET` để trống nếu chưa set
- **PDF Report**: fpdf2 2.8.7, ASCII-safe text (không dùng font Unicode). Gửi thứ 2 07:05 VN qua Telegram sendDocument API
