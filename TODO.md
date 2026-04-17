# TODO — Affiliate Marketing Automation

> Cập nhật lần cuối: 17/04/2026 (phiên 8 — Frontend TikTok Studio)

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

## Bước tiếp theo (Phase 3 — Content Production)

### Ưu tiên cao
- [x] **Frontend TikTok Studio** — `sidebar.tsx` (2 sections mới), `/tiktok-studio` (Kanban board), `/tiktok-studio/new` (3-step wizard), `/tiktok-studio/[id]` (4 tabs: Kịch bản, Assets, Checklist, Timeline)
- [ ] **ElevenLabs setup thật** — clone giọng bạn (upload 1-2 phút audio sạch) → Voice ID → điền Settings
- [ ] **HeyGen setup thật** — tạo Photo Avatar / Digital Twin → Avatar ID + Voice ID → điền Settings
- [ ] **Test end-to-end** — chạy pipeline với `tiktok_script` → nhận Telegram thông báo link MP3 + MP4 clips
- [ ] **Facebook Publisher** — chờ thiết bị được tin tưởng → tạo Meta Developer App → Page Token → test đăng bài thật
- [ ] **TikTok video upload** — tạo slide MP4 từ ảnh sản phẩm → upload vào `upload_url` → post thật (hoặc edit CapCut + upload web UI)

### Ưu tiên trung bình
- [ ] **Multi-account support** — nhiều Facebook Page, nhiều WordPress site (phức tạp: DB migration + UI + publisher routing)
- [ ] **Gemini Vision test thật** — quota reset hàng ngày, test với ảnh thật Shopee/Tiki

### Ưu tiên thấp
- [ ] Sync/cập nhật ECC skills & agents (hiện có 57 skills, 47 agents)

### Ghi chú còn tồn từ các phiên trước
> **TikTok giới hạn:** API chỉ nhận VIDEO, không có text-only post. Draft hiện tại có `publish_id` và `upload_url` hợp lệ từ TikTok. Để post thật cần upload file video MP4 vào `upload_url` đó.
>
> **Ngrok/Sandbox:** Token TikTok sandbox hết hạn sau 24h. Cần re-auth qua `/auth/tiktok` mỗi ngày. Production sẽ có refresh_token.

---

## Lịch sử hoàn thành (mới → cũ)

### Phiên 8 (17/04/2026) — Frontend TikTok Studio
- [x] **TikTokProject types** — thêm `TikTokProject`, `TikTokAngle`, `TikTokStatus` vào `frontend/src/lib/types.ts`
- [x] **Sidebar** — thêm section "TIKTOK STUDIO" (🎬 TikTok Studio + ➕ Dự án mới)
- [x] **`/tiktok-studio`** — Kanban board 5 cột (Kịch bản, Audio, Clips, Dựng phim, Hoàn thành), stats row 3 card, empty state
- [x] **`/tiktok-studio/new`** — Wizard 3 bước: Thông tin SP → Góc tiếp cận (pain_point/feature/social_proof) → Xác nhận & tạo
- [x] **`/tiktok-studio/[id]`** — Detail 4 tabs: Kịch bản (view/copy/tạo lại), Assets (audio player + download MP3/MP4), Checklist (B-roll/Dựng/Upload + form hiệu suất), Timeline (milestone + stats)
- [x] **Build check** — `npm run build` pass 0 lỗi TypeScript, 15 routes OK

### Phiên 7 (16/04/2026) — Security Audit + P1-P3 Fixes
- [x] **Security audit toàn diện** — phát hiện 3 P0 (`.env.prod` + `api.txt` commit public GitHub, GitHub PAT lộ trong `.git/config`) + 10 lỗi P1-P3
- [x] **Rotate keys** — Claude + Gemini + GitHub PAT đã revoke trên provider console
- [x] **Git history rewrite** — `git-filter-repo` scrub `.env.prod` + `api.txt` khỏi 27 commits, force push (e4001d4 → 9880fca)
- [x] **.gitignore hardening** — `.env.*` + `!.env.example`, chặn `backend/static/visuals/*.png`, dev leftovers
- [x] **docker-compose.yml** — bind `127.0.0.1:5432/6379` (không expose ra mạng ngoài)
- [x] **pipeline.py Fail Loud** — thêm `visual_failures` + `content_failures` counter vào `details`, `exc_info=True`
- [x] **Dọn root** — xóa `test_ai_quick.py`, `openapi_check.json`; `build_guide_pdf.py` → `scripts/`
- [x] **CLAUDE.md §3.6** — thêm rule `TÔI XÁC NHẬN XÓA LỊCH SỬ` cho filter-repo + attribution disabled note
- [x] **.claude/settings.local.json** — xóa dòng allow PAT cũ

### Phiên 6 (16/04/2026) — Backend Module Split + TikTok Studio
- [x] **Refactor backend** — tách thành 2 module: `backend/tiktok/` (TikTok Studio) và `backend/affiliate/` (Affiliate Hub). Git mv giữ nguyên history. 140/140 tests pass sau refactor.
- [x] **TikTokProject model** — `backend/models/tiktok_project.py`: 8-stage timeline (script_pending → script_ready → audio_ready → clips_ready → b_roll_filmed → editing → uploaded → live), migration `e5f6a7b8c9d0`
- [x] **TikTok Studio backend** — `backend/tiktok/studio.py` (CRUD), `backend/tiktok/production.py` (pipeline 3 bước: Claude script → ElevenLabs → HeyGen), `backend/tiktok/router.py` (7 endpoints `/api/v1/tiktok-studio/`). 158/158 tests pass.
- [x] **Merge về main** — nhánh `claude/start-new-session-5CEGY` đã merge vào main, push thành công.

### Phiên 5 (14/04/2026) — AI Engines (ElevenLabs + HeyGen)
- [x] **docs/MEMORY.md** — Long-term Memory Bank: tự động cập nhật qua phiên
- [x] **CLAUDE.md cập nhật** — Auto-Memorize rule §3.3a + Start/Save Game đọc/ghi MEMORY.md
- [x] **TikTok Skill SOP** — `docs/skills/tiktok_faceless_affiliate.md`: script faceless review 45–60s, bảng VOICE|VISUAL, checklist 10 điểm
- [x] **ElevenLabs Engine** — `backend/ai_engine/elevenlabs_engine.py`: TTS async, voice clone, `extract_voice_text()`, lưu MP3 vào `/static/audio/`, 18 tests
- [x] **HeyGen Engine** — `backend/ai_engine/heygen_engine.py`: submit clip → async poll → `ClipResult`, hook + CTA song song, 22 tests
- [x] **ContentPiece model mở rộng** — `audio_url`, `audio_voice_id`, `audio_duration_s`, `heygen_hook_url`, `heygen_cta_url`
- [x] **Alembic migrations** — `c3d4e5f6a7b8` (audio) + `d4e5f6a7b8c9` (heygen)
- [x] **Pipeline wired** — ContentGenerator tự động gọi ElevenLabs + HeyGen sau khi tạo `tiktok_script` (non-blocking)

### Phiên 4 (13-14/04/2026) — TikTok OAuth End-to-End
- [x] **TikTok Sandbox setup** — App Key/Secret, Redirect URI, Direct Post ON, scopes (user.info.basic + video.publish + video.upload)
- [x] **TikTok OAuth 2.0 hoàn chỉnh** — `/auth/tiktok` → TikTok → `/auth/tiktok/callback` → token lưu DB
- [x] **Fix bug DB key case** — OAuth callback lưu lowercase, `apply_db_settings()` tìm uppercase → đã fix sang UPPERCASE
- [x] **`GET /auth/tiktok/me`** — test token + lấy user info (open_id, display_name)
- [x] **`GET /publisher/health`** — check tất cả platforms, TikTok: ok, Telegram: ok
- [x] **TikTok publisher fix** — `video_size: 0` → `1` để TikTok trả `publish_id` + `upload_url` hợp lệ
- [x] **Publish end-to-end** — `POST /publisher/publish` → TikTok → `status: published`, `publish_id` thật từ TikTok API

### Phiên 3 (13/04/2026) — AccessTrade + Gemini Pipeline
- [x] **Fix 3 pre-existing test failures** — test_publisher_registry, test_get_publisher_unknown, test_pick_variant_balanced → 78/78 passed
- [x] **AccessTrade connector rewrite** — auth endpoint `/transactions`, mapping deals/coupons (price=0, aff_link, coupon codes)
- [x] **Pipeline filter fix** — bỏ qua price/commission filter cho deals (`is_deal` check)
- [x] **social_post max_tokens** — 500 → 1500, `_strip_thinking_blocks()` xử lý unclosed `<thinking>` tag
- [x] **Settings page fix** — sensitive fields load `""` thay vì `"****"` để user gõ được
- [x] **Gemini model downgrade** — `gemini-2.5-pro` → `gemini-2.0-flash` (quota tier thấp hơn)
- [x] **Pipeline end-to-end thật** — AccessTrade Shopee → 50 deals → 5 lọc → 5 bài Claude Vietnamese → scheduled

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
