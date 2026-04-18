# Kênh 2 Review SOP

**Format:** Semi-auto — owner quay video, AI gen script + tìm affiliate link

## Workflow (tuần)

### Sunday evening (15 phút) — Owner điền input
1. Mở Google Sheet input (URL lưu trong system_settings → `kenh2_input_sheet`)
2. Điền 5-10 SP đang dùng:

| product_name | price_range | category | experience |
|---|---|---|---|
| Sữa bột Meiji | 450-500k | Mẹ&bé | 6 tháng |
| Bỉm Bobby | 250-300k | Mẹ&bé | 1 năm |

### Monday 8h (AI auto-run)
- `google_sheet_poller` chạy 8h sáng
- Parse rows, search TikTok Shop matching product
- Generate 5 script + voice suggestion + B-roll list
- Push vào review queue dashboard

### Mid-week (Owner, 2h batch)
1. Mở review queue → approve 5 script
2. Batch quay 5 video tại nhà (1 buổi ~2h)
3. Dựng trong CapCut (template cố định)
4. Upload qua Tag Queue page (http://localhost:3000/tag-queue)
5. Tag SP → publish

## Quality gate
- KHÔNG gen script nếu SP có ProductScore < 3.0 (Loop 5)
- Từ chối SP có return_rate > 20%
- AI không gen nếu SP chưa có price + affiliate link verified

## Voice style (Kênh 2)
- Dùng ElevenLabs Clone (giọng owner)
- Tone: gần gũi, chia sẻ thật, không sales-y
- Opening pattern: "Mình dùng [X] được [thời gian], và đây là trải nghiệm thật..."
