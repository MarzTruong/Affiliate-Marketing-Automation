# Hook Formula Library — 10 Templates

Dùng Claude Sonnet 4.6 để generate hook theo 1 trong 10 pattern:

## Patterns

1. **pain_point**: "Chị em nào đang đau đầu vì [X]..."
2. **shocking_stat**: "90% mẹ bầu không biết..."
3. **question**: "Bạn có biết SP này ẩn chứa..."
4. **social_proof**: "100,000 mẹ đã dùng và..."
5. **curiosity**: "Thử SP này 7 ngày và đây là kết quả..."
6. **negative**: "Đừng mua [X] nếu bạn chưa biết..."
7. **comparison**: "500k vs 100k — SP nào xịn hơn..."
8. **scarcity**: "Cháy hàng trên Shopee nhưng TikTok Shop còn..."
9. **myth_busting**: "Ai bảo [X] tốt cho bé? Sai rồi..."
10. **tutorial**: "Mẹo dùng [X] mà 95% bà mẹ làm sai..."

## Usage in code

```python
HOOK_PATTERNS = [
    "pain_point", "shocking_stat", "question", "social_proof",
    "curiosity", "negative", "comparison", "scarcity",
    "myth_busting", "tutorial",
]

# Claude prompt: "Generate hook using pattern: {pattern}. Template: {template}"
# Loop 4 picks random pattern, scores by retention@3s after 48h
```

## Hook A/B Test flow (Loop 4)
1. Generate 3 variants (3 different patterns)
2. Randomly pick 1 to post
3. After 48h: pull retention@3s from TikTok Analytics
4. Score variant → running average per pattern
5. After 20 samples: bias generation toward winning patterns
