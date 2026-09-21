from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
import re
from urllib.parse import urlparse

from .deals import assess_deal, record_is_expired


CSV_COLUMNS = (
    "airline",
    "title",
    "status",
    "deal_strength",
    "deal_highlights",
    "relevance",
    "origins",
    "destinations",
    "booking_period",
    "travel_period",
    "first_seen",
    "last_changed",
    "url",
    "summary",
)


def render_csv(state: dict, *, best_only: bool = False) -> bytes:
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    records = []
    for item in state["campaigns"].values():
        if record_is_expired(item):
            continue
        assessment = assess_deal(item)
        if best_only and (assessment.strength != "HIGH" or not assessment.flight_related):
            continue
        records.append((item, assessment))
    if best_only:
        deduplicated = {}
        for item, assessment in records:
            parsed = urlparse(str(item.get("url") or ""))
            path = re.sub(r"-(?:sc|tc|th)$", "", parsed.path.rstrip("/"), flags=re.I)
            key = (item.get("airline", ""), parsed.netloc.lower(), path, tuple(assessment.highlights))
            existing = deduplicated.get(key)
            has_chinese = bool(re.search(r"[\u4e00-\u9fff]", str(item.get("title") or "")))
            existing_has_chinese = bool(
                existing and re.search(r"[\u4e00-\u9fff]", str(existing[0].get("title") or ""))
            )
            if existing is None or (has_chinese and not existing_has_chinese):
                deduplicated[key] = (item, assessment)
        records = list(deduplicated.values())
    records.sort(key=lambda pair: (-pair[1].score, pair[0].get("airline", ""), pair[0].get("title", "")))
    for record, assessment in records:
        writer.writerow(
            {
                "airline": record.get("airline", ""),
                "title": record.get("title", ""),
                "status": "ACTIVE" if record.get("active", True) else "EXPIRED",
                "deal_strength": assessment.strength,
                "deal_highlights": "；".join(assessment.highlights),
                "relevance": record.get("relevance", "general"),
                "origins": "、".join(record.get("matched_origins", [])),
                "destinations": "、".join(record.get("matched_destinations", [])),
                "booking_period": record.get("booking_period", ""),
                "travel_period": record.get("travel_period", ""),
                "first_seen": record.get("first_seen", ""),
                "last_changed": record.get("last_changed", ""),
                "url": record.get("url", ""),
                "summary": record.get("summary", ""),
            }
        )
    return buffer.getvalue().encode("utf-8-sig")


def save_csv_if_changed(path: Path, state: dict, *, best_only: bool = False) -> bool:
    payload = render_csv(state, best_only=best_only)
    if path.exists() and path.read_bytes() == payload:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return True
