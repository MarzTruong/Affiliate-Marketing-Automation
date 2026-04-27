# TODO — Affiliate Marketing Automation

> Cập nhật lần cuối: 27/04/2026 (phiên 15)
> Quy tắc: File này chỉ giữ việc CÒN LÀM + lệnh khởi động + ghi chú kỹ thuật. Lịch sử hoàn thành nén 1 dòng/phiên.

---

## Việc cần làm tiếp theo

### Ưu tiên cao
- [ ] **TikTok dev app — submit review** — upload demo video (~2-3 phút screen record) → Submit for review trên developers.tiktok.com
- [ ] **Plan D' S4** — Frontend Kanban thêm cột "Sẵn sàng đăng" + nút Download MP4 + Copy caption
- [ ] **ElevenLabs clone giọng** — upload 1-2 phút audio sạch → lấy Voice ID mới → điền Settings UI
- [ ] **ElevenLabs test-tts** — test `POST /api/v1/tiktok-studio/test-tts` với `{"text": "..."}` verify giọng tiếng Việt

### Ưu tiên trung bình
- [ ] **Facebook Publisher** — chờ thiết bị được tin tưởng → tạo Meta Developer App → Page Token → test đăng bài thật
- [ ] **TikTok Shop wire** — khi Partner Center app được approve → wire `backend/tiktok_shop/connector.py` với real credentials + test OAuth từng kênh riêng (`TIKTOK_TOKEN_KENH1`, `TIKTOK_TOKEN_KENH2`)
- [ ] **Multi-account support** — nhiều Facebook Page, nhiều WordPress site

### Ưu tiên thấp
- [ ] **HeyGen removal** — xóa HeyGen engine (không dùng cho Kênh 2 nữa)
- [ ] **Gemini Vision test thật** — test với ảnh thật Shopee/Tiki khi quota reset

### Ghi chú tồn đọng
> **TikTok API:** Chỉ nhận VIDEO, không có text-only. Token sandbox hết hạn 24h → re-auth qua `/auth/tiktok` mỗi ngày.
> **TikTok Shop:** Partner Center app "Affiliate Automation" đang chờ approve. CCCD chỉ đăng ký 1 TikTok Shop → kafekaykhe là seller, Lab Gia Dụng chỉ làm affiliate.

---

## Khởi động hệ thống

```bash
# 1. Infra
docker-compose up -d postgres redis

# 2. Backend (root project)
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Frontend
cd frontend && npm run dev
```

| URL | Mục đích |
|-----|----------|
| http://localhost:3000 | Frontend |
| http://localhost:8000/docs | Backend API docs |
| http://localhost:8000/health | Health check |

---

## Ghi chú kỹ thuật quan trọng

- **Credentials:** Platform API keys lưu trong bảng `system_settings` — quản lý qua UI `/settings`. Chỉ `DATABASE_URL`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` trong `.env`
- **Gemini SDK:** Dùng `google-genai` (v1.70.0+) — KHÔNG dùng `google-generativeai` (deprecated). Model: `gemini-2.0-flash`
- **ElevenLabs:** Model `eleven_v3`, đọc từ settings (không hardcode)
- **Venv:** `.venv/` ở root project. Kill server Windows: `powershell.exe -Command "Get-Process python | Stop-Process -Force"`
- **TikTok Shop connector đúng:** `backend/tiktok_shop/connector.py` (HMAC spec chuẩn). KHÔNG dùng `backend/affiliate/connectors/tiktok_shop.py` (đã xóa — bug HMAC)
- **2 kênh:** Kênh 1 "Lab Gia Dụng" → `kenh1_production.py` + `kenh1_publisher.py`. Kênh 2 "Đồ Này Tui Xài" → `kenh2_production.py` + `kenh2_studio.py`
- **Webhook Facebook:** `FACEBOOK_WEBHOOK_SECRET` để trống nếu chưa set → hệ thống skip verify
- **DB settings key:** Lưu UPPERCASE — lowercase sẽ không load được

---

## Lịch sử (tóm tắt)

| Phiên | Ngày | Việc chính |
|-------|------|------------|
| 15 | 27/04 | CLAUDE.md v2, repo audit: xóa HMAC bug, tách code 2 kênh, tổ chức docs, 236 tests xanh |
| 14 | 22/04 | Plan D' Hybrid S1–S3: ffmpeg composer, Telegram notify, TikTok dev app setup guide |
| 13 | 21/04 | ElevenLabs model fix (eleven_v3), channel_type migration, Kling image guard + upscale |
| 12 | 21/04 | Docker orphan fix, ElevenLabs SDK v1 async generator, Kling timeout 600s |
| 11 | 20/04 | TikTok Shop OAuth đúng spec (4 fixes), chiến lược 2 kênh xác nhận, Affiliate Creator API |
| 10 | 20/04 | TikTok Shop Partner Center app tạo thành công, phân tách nguồn SP theo kênh |
| 8 | 17/04 | Frontend TikTok Studio (Kanban, wizard 3 bước, detail 4 tabs) |
| 7 | 16/04 | Security audit P0–P3, git history rewrite, docker bind 127.0.0.1 |
| 6 | 16/04 | Refactor backend → tiktok/ + affiliate/, TikTok Studio backend 7 endpoints |
| 5 | 14/04 | ElevenLabs + HeyGen engines, ContentPiece model mở rộng |
| 4 | 13/04 | TikTok OAuth end-to-end, publisher fix video_size |
| 1-3 | 08-13/04 | Foundation: server setup, Phase 1 features, AccessTrade, Gemini pipeline |
