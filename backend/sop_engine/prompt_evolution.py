"""Prompt evolution engine.

Uses Claude to analyze top-performing templates and generate improved variants.
This creates a feedback loop: score templates -> identify patterns -> evolve prompts.
"""

import logging
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai_engine.client import ClaudeClient
from backend.models.sop_template import SOPTemplate

logger = logging.getLogger(__name__)

EVOLUTION_PROMPT = """Bạn là chuyên gia tối ưu hóa prompt cho hệ thống tiếp thị liên kết.

Dưới đây là template đang hoạt động tốt nhất (điểm: {{ score }}/100):

```
{{ template_text }}
```

Thống kê hiệu suất:
- CTR trung bình: {{ avg_ctr }}%
- Tỷ lệ chuyển đổi: {{ avg_conversion }}%
- Số lần sử dụng: {{ usage_count }}

Hãy tạo một phiên bản CẢI TIẾN của template này bằng tiếng Việt. Yêu cầu:
1. Giữ nguyên cấu trúc Jinja2 ({{ "{{ variable_name }}" }})
2. Tối ưu ngôn ngữ thuyết phục và SEO
3. Thêm yếu tố tạo cảm giác khan hiếm hoặc khẩn cấp (nếu phù hợp)
4. Cải thiện CTA (call-to-action)
5. Tối ưu cho nền tảng Việt Nam (Cốc Cốc, Google.com.vn)

CHỈ trả về template mới, không giải thích."""


async def evolve_template(
    db: AsyncSession,
    source_template_id: uuid.UUID,
) -> SOPTemplate:
    """Create an evolved version of a high-performing template using Claude."""
    source = await db.get(SOPTemplate, source_template_id)
    if not source:
        raise ValueError(f"Template {source_template_id} not found")

    claude = ClaudeClient()

    variables = {
        "score": float(source.performance_score),
        "template_text": source.prompt_template,
        "avg_ctr": float(source.avg_ctr or 0) * 100,
        "avg_conversion": float(source.avg_conversion_rate or 0) * 100,
        "usage_count": source.usage_count,
    }

    evolved_text, usage = await claude.generate(
        content_type="seo_article",  # Use Sonnet for quality
        variables=variables,
        template=EVOLUTION_PROMPT,
        model_override="claude-sonnet-4-6-20260320",
        max_tokens=4000,
    )

    # Create new template as evolved variant
    new_template = SOPTemplate(
        id=uuid.uuid4(),
        name=f"{source.name} (v{source.usage_count + 1})",
        content_type=source.content_type,
        prompt_template=evolved_text.strip(),
        variables=source.variables,
        performance_score=Decimal("0.00"),
        is_active=True,
    )
    db.add(new_template)
    await db.commit()
    await db.refresh(new_template)

    logger.info(
        "Evolved template %s -> %s (%s)",
        source.id, new_template.id, new_template.name,
    )
    return new_template


async def auto_evolve_top_templates(
    db: AsyncSession,
    min_score: float = 50.0,
    min_usage: int = 10,
) -> list[SOPTemplate]:
    """Automatically evolve templates that meet performance thresholds."""
    result = await db.execute(
        select(SOPTemplate).where(
            SOPTemplate.is_active.is_(True),
            SOPTemplate.performance_score >= Decimal(str(min_score)),
            SOPTemplate.usage_count >= min_usage,
        ).order_by(SOPTemplate.performance_score.desc())
    )
    top_templates = result.scalars().all()

    evolved = []
    for tmpl in top_templates:
        try:
            new_tmpl = await evolve_template(db, tmpl.id)
            evolved.append(new_tmpl)
        except Exception:
            logger.exception("Failed to evolve template %s", tmpl.id)

    return evolved
