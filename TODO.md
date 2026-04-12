# TODO — Affiliate Marketing Automation

> Cập nhật lần cuối: 12/04/2026 (phiên 2)

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
- [ ] **Kiểm thử thực tế với API key thật** — nhập AccessTrade key, chạy pipeline với data thật, xem Gemini phân tích ảnh thực tế
- [ ] **Fix 3 pre-existing test failures** — test_publisher_registry, test_get_publisher_unknown, test_pick_variant_balanced

### Ưu tiên trung bình
- [ ] **Multi-account support** — nhiều Facebook Page, nhiều WordPress site (phức tạp: DB migration + UI + publisher routing)

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
- **Gemini models**: `gemini-2.5-pro` (vision), `gemini-2.5-flash` (text)
- **CoT blocks**: Claude trả về `<thinking>...</thinking>` trong output — bị strip bởi `_strip_thinking_blocks()` trước khi lưu DB
- **Venv**: `.venv/` ở root project (không phải trong `backend/`)
- **Log**: `backend.log` và `backend_err.log` ở root project
- **Server rule**: Luôn chạy 1 server duy nhất mỗi port
- **Kill server (Windows)**: `powershell.exe -Command "Get-Process python | Stop-Process -Force"`
- **Webhook Facebook**: `FACEBOOK_WEBHOOK_VERIFY_TOKEN=affiliate_webhook_verify` (default), `FACEBOOK_WEBHOOK_SECRET` để trống nếu chưa set
- **PDF Report**: fpdf2 2.8.7, ASCII-safe text (không dùng font Unicode). Gửi thứ 2 07:05 VN qua Telegram sendDocument API
