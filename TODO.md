# TODO — Affiliate Marketing Automation

> Cập nhật lần cuối: 09/04/2026

---

## Hoàn thành (08–09/04/2026)

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

### Kiểm thử thực tế
- [x] Pipeline end-to-end chạy thành công (mock data): scan → filter → Claude content → pending_review
- [x] Approve/Reject flow hoạt động: AITrainingData được lưu đúng signal
- [x] Bulk approve/reject: `{"approved": 3, "total": 3}` và HTTP 204
- [x] Gemini được gọi trong pipeline: log `[GeminiEngine]` xuất hiện, graceful fallback khi lỗi download

---

## Lỗi / Hạn chế còn tồn đọng

| # | Mức độ | Vấn đề | Ghi chú |
|---|--------|--------|---------|
| 1 | MINOR | Calendar không hiển thị bài `pending_review` | Đã có tab riêng trong Automation, không urgent |
| 2 | MINOR | Hooks ECC cần restart Claude Code | Đường dẫn đã sửa, chưa kiểm tra sau khi restart |
| 3 | INFO | TikTok chỉ hỗ trợ draft mode | Giới hạn của TikTok Content API |
| 4 | INFO | Gemini mock image URLs (placeholder.com) bị block | Sẽ tự resolve khi có ảnh thật từ AccessTrade |

---

## Bước tiếp theo (Phase 2)

### Ưu tiên cao
- [ ] **Kiểm thử thực tế với API key thật** — nhập AccessTrade key, chạy pipeline với data thật, xem Gemini phân tích ảnh Shopee thực tế
- [ ] **Webhook Facebook** — nhận click/reach → Adaptive Scheduler học nhanh hơn

### Ưu tiên trung bình
- [ ] **Báo cáo PDF tự động** — report hàng tuần gửi qua Telegram
- [ ] **Multi-account support** — nhiều Facebook Page, nhiều WordPress site

### Ưu tiên thấp
- [ ] Calendar hiển thị bài `pending_review` (hiện chỉ thấy `scheduled`)
- [ ] Xem full content body trong Review Queue (hiện chỉ preview 200 ký tự)

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
