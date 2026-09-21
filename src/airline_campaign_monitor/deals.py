from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re


ISO_DATE = re.compile(r"(?<!\d)(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})(?!\d)")
CJK_DATE = re.compile(r"(?<!\d)(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日")
SHORT_CJK_DATE = re.compile(r"(?<!年)(?<!\d)(\d{1,2})月\s*(\d{1,2})日")
EN_DATE = re.compile(
    r"(?<!\d)(\d{1,2})\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(20\d{2})(?!\d)",
    re.I,
)
MONTHS = {
    name.lower(): index
    for index, name in enumerate(
        ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"),
        start=1,
    )
}


@dataclass(frozen=True)
class DealAssessment:
    strength: str
    score: int
    highlights: tuple[str, ...]
    flight_related: bool


def extract_dates(text: str) -> list[date]:
    found: set[date] = set()
    for year, month, day in ISO_DATE.findall(text):
        try:
            found.add(date(int(year), int(month), int(day)))
        except ValueError:
            pass
    cjk_matches = CJK_DATE.findall(text)
    for year, month, day in cjk_matches:
        try:
            found.add(date(int(year), int(month), int(day)))
        except ValueError:
            pass
    years = [int(year) for year, _, _ in cjk_matches]
    if years:
        default_year = years[-1]
        for month, day in SHORT_CJK_DATE.findall(text):
            try:
                found.add(date(default_year, int(month), int(day)))
            except ValueError:
                pass
    for day, month, year in EN_DATE.findall(text):
        try:
            found.add(date(int(year), MONTHS[month.lower()], int(day)))
        except ValueError:
            pass
    return sorted(found)


def record_is_expired(record: dict, today: date | None = None) -> bool:
    today = today or date.today()
    if not record.get("active", True):
        return True

    booking_text = str(record.get("booking_period") or "")
    # Some adapters capture a following travel clause in booking_period. Only
    # the sale/booking clause decides whether an offer can still be purchased.
    booking_clause = re.split(r"旅行|出行|搭乘|travel\s+(?:period|date)", booking_text, maxsplit=1, flags=re.I)[0]
    dates = extract_dates(booking_clause)
    if dates:
        return max(dates) < today

    travel_text = str(record.get("travel_period") or "").strip()
    travel_dates = extract_dates(travel_text)
    looks_like_period = bool(re.match(r"^(?:20\d{2}|截至|至\s*20\d{2})", travel_text))
    if travel_dates and looks_like_period:
        return max(travel_dates) < today
    # Dates in a free-form summary may describe an example, an old footnote,
    # or the airline's history. Without a structured booking/travel period we
    # keep the offer until the official listing removes it.
    return False


def assess_deal(record: dict) -> DealAssessment:
    text = " ".join(str(record.get(key) or "") for key in ("title", "summary", "booking_period", "travel_period"))
    lowered = text.lower()
    score = 0
    highlights: list[str] = []
    airline = str(record.get("airline") or "")
    explicit_flight_terms = (
        "航班", "机票", "票价", "航线", "航段", "座位", "奖励机票",
        "flight", "airfare", "fare", "all seats", "award ticket", "flight redemption",
    )
    excluded_product_terms = (
        "行李", "餐食", "酒店", "购物", "租车", "baggage", "meal", "hotel", "krisshop", "car rental",
    )
    flight_related = any(term in lowered for term in explicit_flight_terms)
    if not flight_related and airline in {"ANA", "JAL", "Vietnam Airlines", "AirAsia", "Scoot", "Air China"}:
        flight_related = not any(term in lowered for term in excluded_product_terms)

    percentages = [int(value) for value in re.findall(r"(?<!\d)(\d{1,3})\s*%", text)]
    valid_percentages = [value for value in percentages if value <= 100]
    if valid_percentages:
        best = max(valid_percentages)
        score = max(score, 5 if best >= 25 else 4 if best >= 15 else 2 if best >= 10 else 0)
        if best >= 10:
            highlights.append(f"最高{best}%优惠")

    chinese_discounts = []
    for raw in re.findall(r"(?<!\d)(\d{1,2}(?:\.\d)?)\s*折", text):
        value = float(raw)
        if value > 10:
            value /= 10
        if 0 < value < 10:
            chinese_discounts.append(round((10 - value) * 10))
    if chinese_discounts:
        saving = max(chinese_discounts)
        score = max(score, 5 if saving >= 25 else 4 if saving >= 15 else 2)
        highlights.append(f"约省{saving}%")

    reductions = [int(value) for value in re.findall(r"(?:立减|直减|减免|优惠)[^\d]{0,12}(\d{2,5})\s*元", text)]
    if reductions:
        amount = max(reductions)
        score = max(score, 4 if amount >= 300 else 2 if amount >= 100 else 1)
        highlights.append(f"最高立减{amount}元")

    free_flight = flight_related and any(
        term in lowered
        for term in ("票价免费", "航段免费", "免费机票", "free flight", "complimentary flight", "买一送一", "1-for-1")
    )
    if free_flight:
        score = max(score, 5)
        highlights.append("含免费航段/机票权益")

    if score == 0 and any(term in lowered for term in ("限时特惠", "特价", "special fare", "flash sale")):
        score = 1
        highlights.append("官方特惠价")

    strength = "HIGH" if score >= 4 else "MEDIUM" if score >= 2 else "NORMAL"
    return DealAssessment(strength, score, tuple(dict.fromkeys(highlights)), flight_related)
