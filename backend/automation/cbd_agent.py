"""CBD Agent — Conversation-Based Development.

Cho phép người dùng điều khiển toàn bộ hệ thống qua hội thoại tự nhiên bằng tiếng Việt.
Sử dụng Claude tool_use (function calling) để thực thi các hành động.

Ví dụ:
  User: "Tìm SP điện tử Shopee hoa hồng từ 8%"
  → Agent gọi create_automation_rule(platform="shopee", category="dien_tu", min_commission=8)

  User: "Viết bài review cho tai nghe Sony theo phong cách trẻ trung"
  → Agent gọi generate_content(product_name="Tai nghe Sony", style="trẻ trung")

  User: "Lên lịch đăng tối nay 8 giờ lên Facebook và WordPress"
  → Agent gọi schedule_post(channels=["facebook","wordpress"], hour=20)

  User: "Tuần này campaign nào chạy tốt nhất?"
  → Agent gọi get_analytics_summary(period="week")
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import anthropic

from backend.config import settings

logger = logging.getLogger(__name__)

# Định nghĩa tools cho Claude function calling
CBD_TOOLS = [
    {
        "name": "create_automation_rule",
        "description": "Tạo quy tắc tự động hoá mới: quét SP, tạo content, lên lịch đăng",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Tên quy tắc"},
                "platform": {
                    "type": "string",
                    "enum": ["shopee", "tiktok_shop", "shopback", "accesstrade"],
                    "description": "Nền tảng affiliate",
                },
                "category": {
                    "type": "string",
                    "description": "Danh mục sản phẩm VD: thoi_trang, dien_tu",
                },
                "min_commission_pct": {"type": "number", "description": "Hoa hồng tối thiểu (%)"},
                "min_price": {"type": "number", "description": "Giá tối thiểu (VNĐ)"},
                "max_price": {"type": "number", "description": "Giá tối đa (VNĐ)"},
                "min_rating": {"type": "number", "description": "Rating tối thiểu (0-5)"},
                "channels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Kênh đăng: facebook, wordpress, tiktok",
                },
                "content_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Loại content: social_post, product_description, seo_article",
                },
            },
            "required": ["name", "platform"],
        },
    },
    {
        "name": "trigger_pipeline",
        "description": "Chạy ngay một automation rule cụ thể",
        "input_schema": {
            "type": "object",
            "properties": {
                "rule_name_or_id": {"type": "string", "description": "Tên hoặc ID của rule"},
            },
            "required": ["rule_name_or_id"],
        },
    },
    {
        "name": "generate_content",
        "description": "Tạo nội dung AI cho sản phẩm với phong cách tuỳ chỉnh",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {"type": "string"},
                "content_type": {
                    "type": "string",
                    "enum": ["social_post", "product_description", "seo_article", "video_script"],
                },
                "style": {
                    "type": "string",
                    "description": "Phong cách VD: trẻ trung, chuyên nghiệp, hài hước",
                },
                "platform": {"type": "string", "description": "Nền tảng đăng"},
                "campaign_id": {"type": "string", "description": "ID chiến dịch (tuỳ chọn)"},
            },
            "required": ["product_name", "content_type"],
        },
    },
    {
        "name": "schedule_post",
        "description": "Lên lịch đăng bài vào thời gian cụ thể hoặc giờ tốt nhất tự học",
        "input_schema": {
            "type": "object",
            "properties": {
                "content_id": {"type": "string", "description": "ID bài viết cần đăng"},
                "channels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Kênh: facebook, wordpress, tiktok",
                },
                "scheduled_at": {
                    "type": "string",
                    "description": "ISO datetime hoặc mô tả: 'tối nay 20:00', 'ngày mai 12:00'",
                },
                "use_best_slot": {
                    "type": "boolean",
                    "description": "Tự chọn giờ tốt nhất từ Adaptive Scheduler (mặc định: true)",
                },
            },
            "required": ["content_id", "channels"],
        },
    },
    {
        "name": "get_analytics_summary",
        "description": "Lấy tóm tắt hiệu suất: clicks, conversions, doanh thu, campaign tốt nhất",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["today", "week", "month"],
                    "description": "Khoảng thời gian",
                },
                "metric": {
                    "type": "string",
                    "description": "Metric cụ thể: clicks, conversions, revenue, top_products",
                },
            },
            "required": ["period"],
        },
    },
    {
        "name": "get_schedule_insights",
        "description": "Xem các khung giờ đăng bài hiệu quả nhất theo dữ liệu học được",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "list_automation_rules",
        "description": "Liệt kê tất cả automation rules và trạng thái",
        "input_schema": {
            "type": "object",
            "properties": {
                "active_only": {"type": "boolean"},
            },
        },
    },
    {
        "name": "send_telegram_message",
        "description": "Gửi thông báo tuỳ chỉnh qua Telegram",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
            },
            "required": ["message"],
        },
    },
]

CBD_SYSTEM_PROMPT = """Bạn là AI Assistant của hệ thống Affiliate Marketing Automation.
Bạn nói chuyện bằng tiếng Việt, thân thiện và chuyên nghiệp.

Nhiệm vụ: Giúp người dùng quản lý hệ thống qua hội thoại — tạo rule, chạy pipeline,
tạo content, lên lịch đăng, xem analytics.

Khi người dùng mô tả điều họ muốn, hãy:
1. Hiểu ý định và gọi tool phù hợp
2. Nếu thiếu thông tin quan trọng, hỏi lại trước khi thực hiện
3. Sau khi tool trả kết quả, giải thích rõ ràng bằng tiếng Việt
4. Luôn xác nhận trước khi thực hiện hành động quan trọng (tạo rule, trigger pipeline)

Lưu ý về hệ thống:
- Kênh đăng bài: facebook, wordpress, tiktok (tiktok là draft, cần đăng thủ công)
- Telegram chỉ nhận báo cáo, không đăng bài
- Lịch đăng được tự động tối ưu dựa trên hiệu suất thực tế (Adaptive Scheduler)
- Giờ cao điểm mặc định VN: 12:00, 20:00, 22:00
"""


@dataclass
class ChatMessage:
    role: str  # user | assistant
    content: str


@dataclass
class CBDSession:
    """Session hội thoại — giữ context giữa các tin nhắn."""

    history: list[ChatMessage] = field(default_factory=list)
    db: Any = None  # AsyncSession

    def add_message(self, role: str, content: str) -> None:
        self.history.append(ChatMessage(role=role, content=content))

    def to_anthropic_messages(self) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in self.history]


class CBDAgent:
    """Conversation-Based Development Agent."""

    def __init__(self, db):
        self.db = db
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def chat(self, session: CBDSession, user_message: str) -> str:
        """Xử lý 1 tin nhắn người dùng, trả về phản hồi của agent."""
        session.add_message("user", user_message)

        response = await self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=CBD_SYSTEM_PROMPT,
            tools=CBD_TOOLS,
            messages=session.to_anthropic_messages(),
        )

        # Xử lý tool calls nếu có
        final_text = await self._handle_response(session, response)
        session.add_message("assistant", final_text)
        return final_text

    async def _handle_response(self, session: CBDSession, response) -> str:
        """Xử lý response từ Claude — bao gồm tool calls."""
        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    result = await self._execute_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )

            # Gửi kết quả tool lại cho Claude để tổng hợp câu trả lời
            messages = session.to_anthropic_messages() + [
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": tool_results},
            ]

            follow_up = await self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=CBD_SYSTEM_PROMPT,
                tools=CBD_TOOLS,
                messages=messages,
            )

            return self._extract_text(follow_up)

        return self._extract_text(response)

    def _extract_text(self, response) -> str:
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return "Đã xử lý yêu cầu."

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """Thực thi tool được Claude yêu cầu."""
        try:
            if tool_name == "create_automation_rule":
                return await self._tool_create_rule(tool_input)
            elif tool_name == "trigger_pipeline":
                return await self._tool_trigger_pipeline(tool_input)
            elif tool_name == "generate_content":
                return await self._tool_generate_content(tool_input)
            elif tool_name == "schedule_post":
                return await self._tool_schedule_post(tool_input)
            elif tool_name == "get_analytics_summary":
                return await self._tool_analytics(tool_input)
            elif tool_name == "get_schedule_insights":
                return await self._tool_schedule_insights()
            elif tool_name == "list_automation_rules":
                return await self._tool_list_rules(tool_input)
            elif tool_name == "send_telegram_message":
                return await self._tool_telegram(tool_input)
            else:
                return {"error": f"Tool không tồn tại: {tool_name}"}
        except Exception as e:
            logger.error(f"Tool {tool_name} lỗi: {e}")
            return {"error": str(e)}

    # ── Tool implementations ───────────────────────────────────────────

    async def _tool_create_rule(self, inp: dict) -> dict:
        from decimal import Decimal

        from backend.models.automation import AutomationRule

        channels = inp.get("channels", ["facebook"])
        content_types = inp.get("content_types", ["social_post"])

        rule = AutomationRule(
            name=inp["name"],
            platform=inp["platform"],
            category=inp.get("category"),
            min_commission_pct=Decimal(str(inp["min_commission_pct"]))
            if inp.get("min_commission_pct")
            else None,
            min_price=Decimal(str(inp["min_price"])) if inp.get("min_price") else None,
            max_price=Decimal(str(inp["max_price"])) if inp.get("max_price") else None,
            min_rating=Decimal(str(inp["min_rating"])) if inp.get("min_rating") else None,
            publish_channels={ch: True for ch in channels},
            content_types={ct: True for ct in content_types},
            generate_visual=True,
            is_active=True,
        )
        self.db.add(rule)
        await self.db.commit()
        return {
            "success": True,
            "rule_id": str(rule.id),
            "message": f"Đã tạo rule '{rule.name}' cho {rule.platform}",
        }

    async def _tool_trigger_pipeline(self, inp: dict) -> dict:
        from sqlalchemy import or_, select

        from backend.affiliate.pipeline import run_pipeline
        from backend.models.automation import AutomationRule

        name_or_id = inp["rule_name_or_id"]
        result = await self.db.execute(
            select(AutomationRule).where(
                or_(
                    AutomationRule.name.ilike(f"%{name_or_id}%"),
                    AutomationRule.id.cast(str) == name_or_id,
                )
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            return {"error": f"Không tìm thấy rule: {name_or_id}"}

        run = await run_pipeline(self.db, rule)
        return {
            "success": True,
            "products_filtered": run.products_filtered,
            "content_created": run.content_created,
            "posts_scheduled": run.posts_scheduled,
            "status": run.status,
        }

    async def _tool_generate_content(self, inp: dict) -> dict:
        from backend.ai_engine.client import ClaudeClient
        from backend.ai_engine.prompts.templates import SOCIAL_POST_TEMPLATE

        style = inp.get("style", "thân thiện")
        content_type = inp.get("content_type", "social_post")
        template = SOCIAL_POST_TEMPLATE

        client = ClaudeClient()
        variables = {
            "product_name": inp["product_name"],
            "price": inp.get("price", "Xem thêm"),
            "platform": inp.get("platform", "shopee"),
            "style_note": f"Viết theo phong cách: {style}",
            "affiliate_url": inp.get("affiliate_url", "#"),
            "category": inp.get("category", ""),
            "description": inp.get("description", inp["product_name"]),
            "social_platform": "Facebook",
        }
        content_text, usage = await client.generate(
            content_type=content_type,
            variables=variables,
            template=template,
        )
        return {
            "success": True,
            "content": content_text[:500],
            "full_length": len(content_text),
            "tokens_used": usage.get("output_tokens", 0),
        }

    async def _tool_schedule_post(self, inp: dict) -> dict:
        import uuid

        from backend.affiliate.adaptive_scheduler import get_best_slots, next_scheduled_time
        from backend.models.automation import ScheduledPost

        channels = inp.get("channels", ["facebook"])
        use_best = inp.get("use_best_slot", True)
        content_id = inp.get("content_id")

        if not content_id:
            return {"error": "Thiếu content_id"}

        scheduled_posts = []
        for channel in channels:
            if use_best:
                best_hours = await get_best_slots(self.db, channel, "social_post", n=3)
                sched_time = next_scheduled_time(best_hours)
            else:
                sched_at_str = inp.get("scheduled_at", "")
                sched_time = _parse_scheduled_time(sched_at_str)

            post = ScheduledPost(
                content_id=uuid.UUID(content_id),
                channel=channel,
                scheduled_at=sched_time,
                status="scheduled",
            )
            self.db.add(post)
            scheduled_posts.append(
                {
                    "channel": channel,
                    "scheduled_at": sched_time.strftime("%H:%M %d/%m/%Y"),
                }
            )

        await self.db.commit()
        return {"success": True, "scheduled": scheduled_posts}

    async def _tool_analytics(self, inp: dict) -> dict:
        from datetime import datetime, timedelta, timezone

        from sqlalchemy import func, select

        from backend.models.analytics import AnalyticsEvent

        period = inp.get("period", "week")
        days = {"today": 1, "week": 7, "month": 30}.get(period, 7)
        since = datetime.now(timezone.utc) - timedelta(days=days)

        clicks_r = await self.db.execute(
            select(func.count()).where(
                AnalyticsEvent.event_type == "click",
                AnalyticsEvent.created_at >= since,
            )
        )
        conv_r = await self.db.execute(
            select(func.count()).where(
                AnalyticsEvent.event_type == "conversion",
                AnalyticsEvent.created_at >= since,
            )
        )
        clicks = clicks_r.scalar() or 0
        conversions = conv_r.scalar() or 0

        return {
            "period": period,
            "clicks": clicks,
            "conversions": conversions,
            "ctr": f"{(conversions / clicks * 100):.1f}%" if clicks > 0 else "0%",
        }

    async def _tool_schedule_insights(self) -> dict:
        from backend.affiliate.adaptive_scheduler import get_schedule_insights

        return await get_schedule_insights(self.db)

    async def _tool_list_rules(self, inp: dict) -> dict:
        from sqlalchemy import select

        from backend.models.automation import AutomationRule

        query = select(AutomationRule)
        if inp.get("active_only", True):
            query = query.where(AutomationRule.is_active == True)

        result = await self.db.execute(query)
        rules = result.scalars().all()
        return {
            "rules": [
                {
                    "id": str(r.id),
                    "name": r.name,
                    "platform": r.platform,
                    "is_active": r.is_active,
                    "cron": r.cron_expression,
                }
                for r in rules
            ],
            "total": len(rules),
        }

    async def _tool_telegram(self, inp: dict) -> dict:
        from backend.reports.telegram_reporter import send_custom_message

        success = await send_custom_message(inp["message"])
        return {"success": success}


def _parse_scheduled_time(time_str: str):
    """Parse chuỗi thời gian tự nhiên VN thành datetime."""
    import re
    from datetime import datetime, timedelta

    now = datetime.now()

    # "tối nay 20:00", "ngày mai 12:00"
    if "ngày mai" in time_str.lower():
        base = now + timedelta(days=1)
    else:
        base = now

    match = re.search(r"(\d{1,2}):(\d{2})", time_str)
    if match:
        h, m = int(match.group(1)), int(match.group(2))
        result = base.replace(hour=h, minute=m, second=0, microsecond=0)
        if result <= now:
            result += timedelta(days=1)
        return result

    # Default: giờ cao điểm tiếp theo
    from backend.affiliate.adaptive_scheduler import _default_peak_hours, next_scheduled_time

    return next_scheduled_time(_default_peak_hours())
