from __future__ import annotations

from dataclasses import dataclass
import re

from .deals import assess_deal
from .models import compact_text


CORE_ORIGINS = {
    "HGH": ("杭州", "hangzhou", "hgh"),
    "PVG": ("上海浦东", "浦东", "shanghai pudong", "pvg"),
    "SHA": ("上海虹桥", "虹桥", "shanghai hongqiao", "sha"),
}
SECONDARY_ORIGINS = {
    "NKG": ("南京", "nanjing", "nkg"),
    "NGB": ("宁波", "ningbo", "ngb"),
}
SHANGHAI_TERMS = ("上海", "shanghai")

DESTINATIONS = {
    "日本": ("日本", "japan", "东京", "大阪", "札幌", "福冈", "冲绳", "tokyo", "osaka", "sapporo", "fukuoka", "okinawa"),
    "泰国": ("泰国", "thailand", "曼谷", "bangkok", "清迈", "chiang mai", "普吉", "phuket", "甲米", "krabi"),
    "越南": ("越南", "vietnam", "河内", "hanoi", "胡志明", "ho chi minh", "岘港", "da nang", "芽庄", "nha trang"),
    "东南亚": (
        "东南亚", "southeast asia", "asean", "新加坡", "马来西亚", "印度尼西亚", "印尼", "菲律宾",
        "柬埔寨", "老挝", "缅甸", "文莱", "singapore", "malaysia", "indonesia", "philippines",
        "cambodia", "laos", "myanmar", "brunei", "吉隆坡", "kuala lumpur", "巴厘岛", "bali",
    ),
    "澳大利亚": ("澳大利亚", "澳洲", "australia", "悉尼", "墨尔本", "珀斯", "sydney", "melbourne", "perth"),
    "新西兰": ("新西兰", "new zealand", "奥克兰", "auckland"),
    "欧洲": ("欧洲", "europe", "巴黎", "法兰克福", "罗马", "米兰", "paris", "frankfurt", "rome", "milan"),
    "英国": ("英国", "united kingdom", "britain", "伦敦", "london", "曼彻斯特", "manchester"),
    "北美": ("北美", "north america", "美国", "united states", "加拿大", "canada", "纽约", "new york", "洛杉矶", "los angeles"),
    "南美": ("南美", "south america", "巴西", "brazil", "阿根廷", "argentina"),
    "非洲": ("非洲", "africa", "南非", "south africa", "埃及", "egypt"),
}

# Broad terms are retained for adapter discovery. Notification decisions use
# the stricter promotion and route signals below.
PROMO_TERMS = (
    "促销", "优惠", "特惠", "折扣", "限时", "特价", "低至", "减免", "大促", "双十一", "双11", "11.11", "sale", "deal",
    "offer", "promotion", "promo", "discount", "special fare", "early bird", "campaign",
    "fare", "reward", "redeem", "キャンペーン", "おトク", "割引", "特別", "セール",
)

PROMOTION_SIGNALS = (
    "促销", "优惠活动", "特惠", "折扣码", "优惠码", "特价", "限时优惠", "限时促销", "闪购", "低至", "大促", "双十一", "双11", "11.11",
    "sale", "promotion", "promo code", "discount code", "special fare", "flash sale", "fare sale", "early bird",
    "セール", "割引コード",
)
NEW_ROUTE_TERMS = ("新增航线", "新开航线", "开通航线", "开航", "首航", "复航", "恢复航线", "new route", "launches route", "resumes", "resume service")
FREQUENCY_TERMS = ("加密", "增班", "增加班次", "提升频次", "daily service", "increase frequency", "additional flights")
CAPACITY_PR_TERMS = ("旺季扩张", "增加运力", "扩大运力", "运力投放", "high season", "capacity expansion", "major international expansion")
ROUTE_MARKER = r"(?:出发|始发|起飞|飞往|飞抵|直飞|至|到|\bto\b|→|->|—|–|-|/.*?出发)"


@dataclass(frozen=True)
class FocusAssessment:
    origins: tuple[str, ...]
    destinations: tuple[str, ...]
    relevance: str
    deal_strength: str
    explicit_price: bool
    promotion: bool
    core_route_change: bool
    notify: bool
    reason: str
    score: int


def destination_priority(destinations: tuple[str, ...] | list[str]) -> int:
    """0: Japan/SE Asia; 1: Oceania/Europe/UK; 2: unspecified; 3: Americas/Africa."""
    names = set(destinations)
    if names & {"日本", "泰国", "越南", "东南亚"}:
        return 0
    if names & {"澳大利亚", "新西兰", "欧洲", "英国"}:
        return 1
    if names & {"北美", "南美", "非洲"}:
        return 3
    return 2


def _matches(text: str, groups: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    lowered = compact_text(text).lower()
    return tuple(name for name, terms in groups.items() if any(term.lower() in lowered for term in terms))


def _is_origin(text: str, term: str) -> bool:
    escaped = re.escape(term.lower())
    token = rf"\b{escaped}\b" if term.isascii() and term.isalnum() else escaped
    patterns = (
        rf"(?:from|depart(?:ing|ure)?\s+from)\s+{token}",
        rf"{token}\s*.{{0,12}}{ROUTE_MARKER}",
    )
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def _origin_matches(text: str) -> tuple[str, ...]:
    lowered = compact_text(text).lower()
    found: list[str] = []
    for code, terms in {**CORE_ORIGINS, **SECONDARY_ORIGINS}.items():
        if any(_is_origin(lowered, term) for term in terms):
            found.append(code)

    # "上海出发" cannot distinguish PVG/SHA. Preserve that ambiguity instead
    # of silently choosing one airport.
    if not any(code in found for code in ("PVG", "SHA")) and any(_is_origin(lowered, term) for term in SHANGHAI_TERMS):
        for code in ("PVG", "SHA"):
            if code not in found:
                found.append(code)
    return tuple(found)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term.lower() in text for term in terms)


def _mentions(text: str, term: str) -> bool:
    escaped = re.escape(term.lower())
    pattern = rf"\b{escaped}\b" if term.isascii() and term.isalnum() else escaped
    return bool(re.search(pattern, text, re.I))


def _has_explicit_price(text: str) -> bool:
    currency_before = r"(?:[¥￥$€£]|cny|rmb|usd|aud|nzd|jpy|sgd|thb)\s*\d[\d,.]*"
    currency_after = r"\d[\d,.]*\s*(?:元|人民币|美元|澳元|纽元|日元|新币|泰铢)(?:起|起售|起价)?"
    return bool(re.search(rf"(?:{currency_before}|{currency_after})", text, re.I))


def analyze(text: str, airline: str, *, headline: str | None = None, china_market: bool = False) -> FocusAssessment:
    normalized = compact_text(text)
    lowered = normalized.lower()
    headline_text = compact_text(headline if headline is not None else text).lower()
    # Only a sale headline (not an old footnote buried in the page) can
    # trigger the annual-sale override.
    annual_sale = bool(re.search(
        r"双\s*十\s*一|双\s*11|11[.·/-]?11|black\s*friday|ブラックフライデー",
        headline_text, re.I,
    ))
    mainland_context = bool(re.search(
        r"中国大陆|中国大陸|中国地区|中国出发|中国発|大陆始发|"
        r"杭州|上海|宁波|南京|北京|青岛|广州|深圳|大连|"
        r"hangzhou|shanghai|ningbo|nanjing|beijing|guangzhou|shenzhen",
        lowered, re.I,
    ))
    annual_china_sale = airline in {"ANA", "JAL"} and annual_sale and (china_market or mainland_context)
    origins = _origin_matches(lowered)
    destinations = _matches(lowered, DESTINATIONS)
    # Country-specific Southeast Asia matches also carry the regional label.
    if ("泰国" in destinations or "越南" in destinations) and "东南亚" not in destinations:
        destinations += ("东南亚",)
    core = tuple(code for code in origins if code in CORE_ORIGINS)
    secondary = tuple(code for code in origins if code in SECONDARY_ORIGINS)
    explicit_price = _has_explicit_price(lowered)
    promotion = _contains_any(lowered, PROMOTION_SIGNALS) or bool(
        re.search(r"(?:\d{1,2}(?:\.\d)?\s*折|\d{1,3}\s*%\s*(?:off|discount|优惠|折扣))", lowered, re.I)
    )
    new_route = _contains_any(lowered, NEW_ROUTE_TERMS)
    frequency = _contains_any(lowered, FREQUENCY_TERMS)
    capacity_pr = _contains_any(lowered, CAPACITY_PR_TERMS)
    mentioned_core = tuple(
        code for code, terms in CORE_ORIGINS.items() if any(_mentions(lowered, term) for term in terms)
    )
    core_route_change = bool((core or mentioned_core) and (new_route or frequency))

    score = 5 if (core or core_route_change) else 2 if secondary else 0
    if annual_china_sale:
        score += 10
    score += 4 if explicit_price else 0
    score += 3 if promotion else 0
    score += 3 if core_route_change and new_route else 2 if core_route_change and frequency else 0
    score += max(({"日本": 6, "泰国": 6, "越南": 6, "东南亚": 4,
                   "澳大利亚": 2, "新西兰": 2, "欧洲": 2, "英国": 2}.get(item, 0)
                  for item in destinations), default=0)
    destination_tier = destination_priority(destinations)

    route_news = new_route or frequency or capacity_pr
    foreign_only_route = route_news and not origins
    if foreign_only_route:
        score -= 4
    if route_news and not explicit_price and not promotion:
        score -= 2
    if capacity_pr:
        score -= 2

    meaningful_signal = explicit_price or promotion or core_route_change
    if annual_china_sale:
        relevance = "HIGH"
    elif (core or core_route_change) and meaningful_signal and destination_tier == 0 and score >= 8:
        relevance = "HIGH"
    elif (core or secondary or core_route_change) and meaningful_signal and destination_tier <= 2:
        relevance = "MEDIUM"
    else:
        # Destination keywords alone never raise relevance.
        relevance = "LOW"

    deal = assess_deal({"airline": airline, "title": normalized})
    notify = relevance == "HIGH" or (
        relevance == "MEDIUM" and (explicit_price or promotion or core_route_change)
    )

    origin_text = "核心出发地 " + "/".join(core) if core else (
        "涉及核心机场 " + "/".join(mentioned_core) if core_route_change else
        "次级出发地 " + "/".join(secondary) if secondary else "无中国大陆核心或次级出发地"
    )
    destination_text = " + ".join(destinations) + "目的地" if destinations else "未识别目的地区域"
    signal_parts = []
    if explicit_price:
        signal_parts.append("明确促销价格")
    elif promotion:
        signal_parts.append("明确促销活动")
    if core_route_change:
        signal_parts.append("核心机场航线新增/复航/加密")
    if foreign_only_route:
        signal_parts.append("仅境外航线变化")
    if capacity_pr:
        signal_parts.append("仅旺季扩张/运力 PR")
    if annual_china_sale:
        signal_parts.append("双十一/黑五中国市场专项监测")
    if not signal_parts:
        signal_parts.append("无明确价格或促销")
    reason = " + ".join((origin_text, destination_text, *signal_parts))

    return FocusAssessment(
        origins=origins,
        destinations=destinations,
        relevance=relevance,
        deal_strength=deal.strength,
        explicit_price=explicit_price,
        promotion=promotion,
        core_route_change=core_route_change,
        notify=notify,
        reason=reason,
        score=score,
    )


def classify(text: str, airline: str) -> tuple[tuple[str, ...], tuple[str, ...], str]:
    """Backward-compatible view for integrations using the old helper."""
    result = analyze(text, airline)
    return result.origins, result.destinations, result.relevance
