"""Post-edit hook: warn khi file Python vừa edit nuốt exception silently.

CLAUDE.md §1 — Fail Loud: mọi `except` phải `logger.error(...) + raise`.
Patterns bị cấm:
- `except X: pass`
- `except X: return None`
- `except X: return` (no value)

Hook đọc tool input JSON từ stdin, nếu file là `.py` trong `backend/` thì quét.
Warn (không block) để tránh false positive phá workflow.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SILENT_PATTERNS = [
    re.compile(r"^\s*except[^:]*:\s*pass\s*$", re.MULTILINE),
    re.compile(r"^\s*except[^:]*:\s*return\s+None\s*$", re.MULTILINE),
    re.compile(r"^\s*except[^:]*:\s*return\s*$", re.MULTILINE),
]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path")
    if not file_path:
        return 0

    path = Path(file_path)
    if path.suffix != ".py":
        return 0
    if "backend" not in path.parts:
        return 0
    if not path.exists():
        return 0

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return 0

    hits: list[str] = []
    for pat in SILENT_PATTERNS:
        for m in pat.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            hits.append(f"  line {line_no}: {m.group(0).strip()}")

    if hits:
        print(
            f"[HOOK WARN] Silent exception swallow trong {path.name} — "
            "CLAUDE.md §1 yêu cầu log.error + raise:",
            file=sys.stderr,
        )
        for h in hits:
            print(h, file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
