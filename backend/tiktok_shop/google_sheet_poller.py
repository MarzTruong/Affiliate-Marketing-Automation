"""GoogleSheetPoller — poll Kênh 2 input list from Google Sheet CSV export.

Uses Google Sheets public CSV export API (no OAuth needed if sheet is shared
"anyone with link can view"). Owner fills sheet weekly with products they own.
"""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GoogleSheetConfig:
    sheet_id: str
    tab_name: str = "Kenh2Input"
    timeout_seconds: float = 15.0


@dataclass(frozen=True)
class Kenh2Product:
    product_name: str
    price_range: str
    category: str
    experience: str


class GoogleSheetPoller:
    def __init__(self, config: GoogleSheetConfig) -> None:
        self.config = config

    async def poll(self) -> list[Kenh2Product]:
        """Fetch sheet CSV, parse rows, skip empty product_name rows."""
        csv_text = await self._fetch_csv()
        reader = csv.DictReader(io.StringIO(csv_text))
        out: list[Kenh2Product] = []
        for row in reader:
            name = (row.get("product_name") or "").strip()
            if not name:
                continue
            out.append(
                Kenh2Product(
                    product_name=name,
                    price_range=(row.get("price_range") or "").strip(),
                    category=(row.get("category") or "").strip(),
                    experience=(row.get("experience") or "").strip(),
                )
            )
        return out

    async def _fetch_csv(self) -> str:
        url = (
            f"https://docs.google.com/spreadsheets/d/{self.config.sheet_id}"
            f"/gviz/tq?tqx=out:csv&sheet={self.config.tab_name}"
        )
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
