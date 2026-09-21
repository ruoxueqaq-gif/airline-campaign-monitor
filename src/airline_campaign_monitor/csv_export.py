from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path


CSV_COLUMNS = (
    "airline",
    "title",
    "status",
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


def render_csv(state: dict) -> bytes:
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    records = sorted(
        state["campaigns"].values(),
        key=lambda item: (item.get("airline", ""), not item.get("active", True), item.get("title", "")),
    )
    for record in records:
        writer.writerow(
            {
                "airline": record.get("airline", ""),
                "title": record.get("title", ""),
                "status": "ACTIVE" if record.get("active", True) else "EXPIRED",
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


def save_csv_if_changed(path: Path, state: dict) -> bool:
    payload = render_csv(state)
    if path.exists() and path.read_bytes() == payload:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return True

