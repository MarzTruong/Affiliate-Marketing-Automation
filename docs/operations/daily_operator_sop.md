# Daily Operator SOP

Tổng thời gian: ~35-45 phút/ngày

## Sáng (15 phút)

**Checklist:**
- [ ] Check Telegram alert qua đêm (error, viral hit)
- [ ] Mở review queue: approve 5-10 video Kênh 1 AI gen
- [ ] Check Tag Queue backlog (phải < 10 video chờ)

**Quick commands:**
```bash
# Health check
curl http://localhost:8000/health

# Review queue count
curl http://localhost:8000/api/review-queue/count

# Tag queue pending count
curl http://localhost:8000/api/tag-queue/pending | python -c "import sys,json; d=json.load(sys.stdin); print(f'Pending: {len(d)}')"
```

## Tối (20-30 phút)

**Checklist:**
- [ ] Mở http://localhost:3000/tag-queue
- [ ] Tag 3-5 video (click "Mở TikTok Draft" → tag SP → quay lại → "Đã publish")
- [ ] Check retention@3s của video đã post 24h trước
- [ ] Note hook nào thắng (Telegram saved messages)

## Red flags — dừng ngay
- 2+ video liên tiếp < 200 views sau 48h → report ngay, xem xét pause gen
- TikTok gửi cảnh báo chính sách → dừng post 24h, đọc kỹ cảnh báo
- AI cost > 5M VND/tháng → check cost_tracker, adjust daily cap

## Dashboard URLs
| Dashboard | URL |
|---|---|
| Tag Queue | http://localhost:3000/tag-queue |
| Review Queue | http://localhost:3000/content |
| Analytics | http://localhost:3000/analytics |
| Backend API docs | http://localhost:8000/docs |
