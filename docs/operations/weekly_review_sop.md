# Weekly Review SOP

Thời gian: ~1h mỗi Chủ nhật

## Checklist

### Data pull (15 phút)
- [ ] Doanh thu tuần (TikTok Shop Creator Center + DB query bên dưới)
- [ ] Top 3 video viral (view + CTR cao nhất)
- [ ] Bottom 3 video flop (view thấp nhất sau 72h)
- [ ] Hook A/B winner của tuần

```bash
# Weekly revenue summary
curl "http://localhost:8000/api/reports/weekly?week=current"

# Top hooks this week
curl "http://localhost:8000/api/learning/hook-patterns/top?limit=3"
```

### Analysis (20 phút)
- [ ] Pattern top 3: hook type nào? Pillar nào? Sub-niche nào?
- [ ] Lesson bottom 3: hook sai? SP sai? Timing sai?
- [ ] Bất kỳ SP nào return > 20%? → note để Loop 5 blacklist

### Planning (25 phút)
- [ ] Plan 5 SP cho Kênh 2 tuần tới → điền vào Google Sheet input
- [ ] Nếu có hook pattern thắng liên tục 3+ tuần → cân nhắc tăng tỉ trọng
- [ ] Nếu sub-niche nào đang outperform → xem xét tăng tỉ lệ Pillar

## Kill switch check (cuối tháng 3)
- Kênh 1 avg views < 500 → báo cho dev, pause 50% volume
- Total revenue tháng 6 < 5M VND → họp pivot hoặc dừng Kênh 1
