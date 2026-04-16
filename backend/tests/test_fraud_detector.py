"""Tests for fraud detection engine."""

from datetime import datetime, timedelta
from decimal import Decimal

from backend.analytics.fraud_detector import FraudDetector
from backend.models.analytics import AnalyticsEvent


def _make_event(event_type: str, ip: str = "1.2.3.4", time_offset_sec: int = 0, campaign_id=None):
    e = AnalyticsEvent()
    e.id = abs(hash(f"{ip}{event_type}{time_offset_sec}")) % 1000000
    e.event_type = event_type
    e.platform = "shopee"
    e.campaign_id = campaign_id
    e.event_time = datetime(2026, 4, 5, 12, 0, 0) + timedelta(seconds=time_offset_sec)
    e.metadata_json = {"ip": ip}
    e.value = Decimal("1000") if event_type == "revenue" else None
    return e


def test_no_fraud_normal_traffic():
    detector = FraudDetector()
    events = [_make_event("click", ip=f"10.0.0.{i}", time_offset_sec=i * 60) for i in range(5)]
    alerts = detector.analyze(events)
    assert len(alerts) == 0


def test_click_spam_detection():
    detector = FraudDetector()
    # 15 clicks from same IP in same hour
    events = [_make_event("click", ip="1.2.3.4", time_offset_sec=i * 10) for i in range(15)]
    alerts = detector.analyze(events)
    fraud_types = [a.fraud_type for a in alerts]
    assert "click_spam" in fraud_types


def test_timing_anomaly_detection():
    detector = FraudDetector()
    # 12 clicks at exact 1-second intervals from same IP
    events = [_make_event("click", ip="5.5.5.5", time_offset_sec=i) for i in range(12)]
    alerts = detector.analyze(events)
    fraud_types = [a.fraud_type for a in alerts]
    assert "timing_anomaly" in fraud_types


def test_conversion_spike_detection():
    detector = FraudDetector()
    # 20 clicks, 10 conversions = 50% rate (way above 15% threshold)
    events = [_make_event("click", ip=f"10.0.0.{i}") for i in range(20)]
    events += [_make_event("conversion", ip=f"10.0.0.{i}") for i in range(10)]
    alerts = detector.analyze(events)
    fraud_types = [a.fraud_type for a in alerts]
    assert "conversion_rate_spike" in fraud_types


def test_no_conversion_spike_low_volume():
    detector = FraudDetector()
    # Only 5 clicks - below threshold of 10
    events = [_make_event("click", ip=f"10.0.0.{i}") for i in range(5)]
    events += [_make_event("conversion", ip=f"10.0.0.{i}") for i in range(4)]
    alerts = detector.analyze(events)
    fraud_types = [a.fraud_type for a in alerts]
    assert "conversion_rate_spike" not in fraud_types


def test_normal_conversion_rate():
    detector = FraudDetector()
    # 100 clicks, 3 conversions = 3% (normal)
    events = [
        _make_event("click", ip=f"10.0.0.{i % 256}", time_offset_sec=i * 60) for i in range(100)
    ]
    events += [_make_event("conversion", ip=f"10.0.0.{i}") for i in range(3)]
    alerts = detector.analyze(events)
    fraud_types = [a.fraud_type for a in alerts]
    assert "conversion_rate_spike" not in fraud_types
