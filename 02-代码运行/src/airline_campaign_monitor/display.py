from __future__ import annotations

from functools import lru_cache
import re

import requests


# Translation affects presentation only. The official text remains in the source
# fields for change detection and for checking the linked airline page.
TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
FIELDS = ("title", "summary", "booking_period", "travel_period")


def needs_translation(value: str) -> bool:
    kana = bool(re.search(r"[\u3040-\u30ff]", value))
    latin = len(re.findall(r"[A-Za-z]", value))
    han = len(re.findall(r"[\u4e00-\u9fff]", value))
    return kana or (latin >= 6 and latin > han)


@lru_cache(maxsize=2048)
def _translate(value: str) -> str:
    response = requests.get(
        TRANSLATE_URL,
        params={"client": "gtx", "sl": "auto", "tl": "zh-CN", "dt": "t", "q": value},
        timeout=12,
        headers={"User-Agent": "Mozilla/5.0 airline-campaign-monitor/1.0"},
    )
    response.raise_for_status()
    translated = "".join(segment[0] for segment in response.json()[0] if segment and segment[0]).strip()
    if not re.search(r"[\u4e00-\u9fff]", translated):
        raise ValueError("翻译结果没有中文内容")
    return translated


def display_text(value: str, field: str) -> tuple[str, bool]:
    if not value or not needs_translation(value):
        return value, False
    try:
        return _translate(value), False
    except (requests.RequestException, ValueError, IndexError, KeyError, TypeError):
        fallback = {
            "title": "促销活动（中文翻译暂不可用）",
            "summary": "中文翻译暂不可用，请打开官方链接查看活动详情。",
            "booking_period": "购票期请以官方页面为准",
            "travel_period": "旅行期请以官方页面为准",
        }
        return fallback[field], True


def localize_record(record: dict, previous: dict | None = None) -> dict:
    pending = False
    for field in FIELDS:
        value = str(record.get(field) or "")
        key = field + "_zh"
        if (
            previous is not None
            and value == str(previous.get(field) or "")
            and previous.get(key)
            and not previous.get("translation_pending")
        ):
            record[key] = previous[key]
        else:
            record[key], failed = display_text(value, field)
            pending |= failed
    record["translation_pending"] = pending
    return record


def shown(record: dict, field: str) -> str:
    value = record.get(field + "_zh")
    if value is not None:
        return str(value)
    return display_text(str(record.get(field) or ""), field)[0]

AIRLINE_NAMES = {
    "ANA": "全日空", "JAL": "日本航空", "Vietnam Airlines": "越南航空",
    "AirAsia": "亚洲航空", "Scoot": "酷航", "Singapore Airlines": "新加坡航空",
    "Air China": "中国国际航空",
}
RELEVANCE_NAMES = {"HIGH": "高", "MEDIUM": "中", "LOW": "低"}
DEAL_NAMES = {"GREAT": "很划算", "GOOD": "较好", "NORMAL": "普通"}
STATUS_NAMES = {"NEW": "新增", "UPDATED": "更新", "EXPIRED": "结束"}
