# Monthly Pivot SOP

Thời gian: ~2h cuối tháng

## Financial review

### P&L per kênh
```bash
curl "http://localhost:8000/api/reports/monthly?month=current"
```

So sánh với kế hoạch spec:
| Month | EV Revenue | EV Net |
|---|---|---|
| 1-2 | 3-5M | âm (test) |
| 3-4 | 10-20M | break-even |
| 5-6 | 20-40M | 5-15M net |
| 7-12 | 50-100M/tháng | 30-60M net |

## Kill switch criteria

- [ ] **Tháng 3:** Kênh 1 avg views < 500 → pause 50% volume, điều tra
- [ ] **Tháng 6:** Total revenue < 5M → họp pivot hoặc dừng Kênh 1
- [ ] **Bất kỳ lúc:** Return rate > 30% → pause 2 tuần, vet lại toàn bộ SP
- [ ] **Bất kỳ lúc:** TikTok cảnh báo lần 2 → chuyển sang Reels/Shorts

## Product blacklist review
```bash
# List blacklisted products
curl "http://localhost:8000/api/learning/product-scores?status=blacklisted"
```
- Review lý do blacklist
- Nếu return rate đã giảm (SP cải tiến) → có thể unblacklist thủ công

## Phase adjustment checklist
- [ ] Phase còn đúng không? (Warm Up → Growth → Scale)
- [ ] AI cost cap cần điều chỉnh không?
- [ ] Content pillar ratio cần thay đổi không?
- [ ] Cần thuê editor cho Kênh 2 chưa? (khi revenue > 15M/tháng)

## TikTok Shop Developer status check
- [ ] Custom App còn active không? (gọi API test đơn giản)
- [ ] Access token còn hạn không? (refresh nếu cần)
- [ ] Scopes còn đủ không? (check sau TikTok policy update)
