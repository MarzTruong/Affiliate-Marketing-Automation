"""Test GoogleSheetPoller — Kênh 2 input from Google Sheets."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.tiktok_shop.google_sheet_poller import (
    GoogleSheetConfig,
    GoogleSheetPoller,
    Kenh2Product,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_poll_parses_rows_into_products():
    cfg = GoogleSheetConfig(sheet_id="sheet_abc")
    poller = GoogleSheetPoller(cfg)

    fake_csv = (
        "product_name,price_range,category,experience\n"
        "Sữa bột Meiji,450-500k,Mẹ&bé,6 tháng\n"
        "Bỉm Bobby,250-300k,Mẹ&bé,1 năm\n"
    )
    with patch.object(poller, "_fetch_csv", new=AsyncMock(return_value=fake_csv)):
        products = await poller.poll()

    assert len(products) == 2
    assert isinstance(products[0], Kenh2Product)
    assert products[0].product_name == "Sữa bột Meiji"
    assert products[0].category == "Mẹ&bé"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_poll_skips_empty_product_name_rows():
    cfg = GoogleSheetConfig(sheet_id="x")
    poller = GoogleSheetPoller(cfg)
    fake_csv = (
        "product_name,price_range,category,experience\n"
        ",,,\n"
        "Meiji,450k,baby,1y\n"
    )
    with patch.object(poller, "_fetch_csv", new=AsyncMock(return_value=fake_csv)):
        products = await poller.poll()
    assert len(products) == 1
    assert products[0].product_name == "Meiji"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_poll_returns_empty_for_header_only_sheet():
    cfg = GoogleSheetConfig(sheet_id="x")
    poller = GoogleSheetPoller(cfg)
    fake_csv = "product_name,price_range,category,experience\n"
    with patch.object(poller, "_fetch_csv", new=AsyncMock(return_value=fake_csv)):
        products = await poller.poll()
    assert products == []


@pytest.mark.unit
def test_config_defaults():
    cfg = GoogleSheetConfig(sheet_id="x")
    assert cfg.tab_name == "Kenh2Input"
    assert cfg.timeout_seconds == 15.0
