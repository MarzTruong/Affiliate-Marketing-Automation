"""Rule-based fraud detection for affiliate marketing."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.analytics import AnalyticsEvent
from backend.models.fraud_event import FraudEvent


class FraudDetector:
    """Detect suspicious patterns in analytics events."""

    def analyze(self, events: list[AnalyticsEvent]) -> list[FraudEvent]:
        flagged = []
        flagged.extend(self._check_click_frequency(events))
        flagged.extend(self._check_timing_patterns(events))
        flagged.extend(self._check_conversion_spike(events))
        return flagged

    def _check_click_frequency(
        self, events: list[AnalyticsEvent], max_per_ip_per_hour: int = 10
    ) -> list[FraudEvent]:
        """Flag IPs with abnormally high click counts."""
        clicks = [e for e in events if e.event_type == "click"]
        ip_hour_counts: dict[tuple[str, str], list[AnalyticsEvent]] = defaultdict(list)

        for click in clicks:
            ip = (click.metadata_json or {}).get("ip", "unknown")
            hour = click.event_time.strftime("%Y-%m-%d-%H")
            ip_hour_counts[(ip, hour)].append(click)

        flagged = []
        for (ip, hour), group in ip_hour_counts.items():
            if len(group) > max_per_ip_per_hour:
                flagged.append(
                    FraudEvent(
                        analytics_event_id=group[0].id,
                        campaign_id=group[0].campaign_id,
                        fraud_type="click_spam",
                        confidence=Decimal("0.85"),
                        details={
                            "ip": ip,
                            "hour": hour,
                            "click_count": len(group),
                            "threshold": max_per_ip_per_hour,
                        },
                    )
                )
        return flagged

    def _check_timing_patterns(
        self, events: list[AnalyticsEvent], min_interval_seconds: int = 2
    ) -> list[FraudEvent]:
        """Flag clicks arriving at suspiciously regular intervals."""
        clicks = sorted(
            [e for e in events if e.event_type == "click"],
            key=lambda e: e.event_time,
        )

        # Group by IP
        ip_clicks: dict[str, list[AnalyticsEvent]] = defaultdict(list)
        for click in clicks:
            ip = (click.metadata_json or {}).get("ip", "unknown")
            ip_clicks[ip].append(click)

        flagged = []
        for ip, group in ip_clicks.items():
            if len(group) < 5:
                continue
            intervals = []
            for i in range(1, len(group)):
                diff = (group[i].event_time - group[i - 1].event_time).total_seconds()
                intervals.append(diff)

            # Check if intervals are suspiciously uniform
            if intervals and all(abs(i - intervals[0]) < 0.5 for i in intervals):
                if intervals[0] < min_interval_seconds or len(intervals) > 10:
                    flagged.append(
                        FraudEvent(
                            analytics_event_id=group[0].id,
                            campaign_id=group[0].campaign_id,
                            fraud_type="timing_anomaly",
                            confidence=Decimal("0.90"),
                            details={
                                "ip": ip,
                                "avg_interval_seconds": sum(intervals) / len(intervals),
                                "click_count": len(group),
                            },
                        )
                    )
        return flagged

    def _check_conversion_spike(
        self, events: list[AnalyticsEvent], z_threshold: float = 3.0
    ) -> list[FraudEvent]:
        """Flag abnormal conversion rate spikes."""
        clicks = len([e for e in events if e.event_type == "click"])
        conversions = len([e for e in events if e.event_type == "conversion"])

        if clicks < 10:
            return []

        rate = conversions / clicks
        # Normal e-commerce conversion rate is 1-3%
        if rate > 0.15:  # 15% conversion rate is very suspicious
            return [
                FraudEvent(
                    campaign_id=events[0].campaign_id if events else None,
                    fraud_type="conversion_rate_spike",
                    confidence=Decimal(str(min(rate / 0.15, 1.0))),
                    details={
                        "clicks": clicks,
                        "conversions": conversions,
                        "rate": round(rate * 100, 2),
                    },
                )
            ]
        return []

    async def scan_recent(self, db: AsyncSession, hours: int = 1) -> list[FraudEvent]:
        """Scan recent analytics events for fraud and persist alerts."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await db.execute(
            select(AnalyticsEvent).where(AnalyticsEvent.event_time >= since)
        )
        events = list(result.scalars().all())

        if not events:
            return []

        flagged = self.analyze(events)
        for alert in flagged:
            db.add(alert)
        if flagged:
            await db.commit()
        return flagged
