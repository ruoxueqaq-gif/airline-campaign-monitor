from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
import re
from urllib.parse import urlparse

from .deals import assess_deal, record_is_expired
from .display import AIRLINE_NAMES, DEAL_NAMES, RELEVANCE_NAMES, shown
from .focus import destination_priority


CSV_COLUMNS = (
    "airline",
    "title",
    "status",
    "deal_strength",
    "deal_highlights",
    "relevance",
    "origins",
    "destinations",
    "has_explicit_price",
    "notify",
    "reason",
    "booking_period",
    "travel_period",
    "first_seen",
    "last_changed",
    "url",
    "summary",
)

CSV_HEADERS = {
    "airline": "航空公司", "title": "促销标题", "status": "状态", "deal_strength": "优惠力度",
    "deal_highlights": "优惠亮点", "relevance": "相关度", "origins": "出发地", "destinations": "目的地",
    "has_explicit_price": "是否有明确价格", "notify": "是否通知", "reason": "判断原因",
    "booking_period": "预订日期", "travel_period": "旅行日期",
    "first_seen": "首次发现时间", "last_changed": "最后更新时间", "url": "官方链接", "summary": "摘要",
}


def render_csv(state: dict, *, best_only: bool = False) -> bytes:
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=[CSV_HEADERS[name] for name in CSV_COLUMNS], lineterminator="\n")
    writer.writeheader()
    records = []
    for item in state["campaigns"].values():
        if record_is_expired(item):
            continue
        assessment = assess_deal(item)
        if best_only and (assessment.strength != "GREAT" or not assessment.flight_related):
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
    records.sort(key=lambda pair: (destination_priority(pair[0].get("destination_match") or pair[0].get("matched_destinations") or []),
                                   -int(pair[0].get("relevance_score") or 0), -pair[1].score,
                                   pair[0].get("airline", ""), pair[0].get("title", "")))
    for record, assessment in records:
        row = {
                "airline": AIRLINE_NAMES.get(record.get("airline", ""), record.get("airline", "")),
                "title": shown(record, "title"),
                "status": "进行中" if record.get("active", True) else "已结束",
                "deal_strength": DEAL_NAMES.get(record.get("deal_strength") or assessment.strength, "普通"),
                "deal_highlights": "；".join(assessment.highlights),
                "relevance": RELEVANCE_NAMES.get(record.get("relevance", "LOW"), "低"),
                "origins": "、".join(record.get("origin_match") or record.get("matched_origins", [])),
                "destinations": "、".join(record.get("destination_match") or record.get("matched_destinations", [])),
                "has_explicit_price": "是" if record.get("has_explicit_price") else "否",
                "notify": "是" if record.get("notify") else "否",
                "reason": record.get("reason", ""),
                "booking_period": shown(record, "booking_period"),
                "travel_period": shown(record, "travel_period"),
                "first_seen": record.get("first_seen", ""),
                "last_changed": record.get("last_changed", ""),
                "url": record.get("url", ""),
                "summary": shown(record, "summary"),
            }
        writer.writerow({CSV_HEADERS[key]: value for key, value in row.items()})
    return buffer.getvalue().encode("utf-8-sig")


def save_csv_if_changed(path: Path, state: dict, *, best_only: bool = False) -> bool:
    payload = render_csv(state, best_only=best_only)
    if path.exists() and path.read_bytes() == payload:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return True
