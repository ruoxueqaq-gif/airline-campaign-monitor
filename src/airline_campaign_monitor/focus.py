from __future__ import annotations

from .models import compact_text

ORIGINS = {
    "上海": ("上海", "shanghai", "pvg", "sha"),
    "杭州": ("杭州", "hangzhou", "hgh"),
    "北京": ("北京", "beijing", "pek", "pkx"),
    "广州": ("广州", "guangzhou", "can"),
    "深圳": ("深圳", "shenzhen", "szx"),
    "厦门": ("厦门", "xiamen", "xmn"),
    "中国大陆": ("中国大陆", "mainland china", "china departure", "中国出发"),
}

DESTINATIONS = {
    "日本": ("日本", "japan", "东京", "大阪", "札幌", "福冈", "冲绳", "tokyo", "osaka", "sapporo"),
    "东南亚": ("东南亚", "southeast asia", "新加坡", "越南", "泰国", "马来西亚", "印尼", "菲律宾", "柬埔寨", "singapore", "vietnam", "thailand", "malaysia", "bali"),
    "澳大利亚": ("澳大利亚", "澳洲", "australia", "悉尼", "墨尔本", "珀斯", "sydney", "melbourne", "perth"),
    "新西兰": ("新西兰", "new zealand", "奥克兰", "auckland"),
    "欧洲": ("欧洲", "europe", "伦敦", "巴黎", "法兰克福", "罗马", "米兰", "london", "paris", "frankfurt", "rome", "milan"),
}

PROMO_TERMS = (
    "促销", "优惠", "特惠", "折扣", "限时", "特价", "低至", "减免", "sale", "deal",
    "offer", "promotion", "promo", "discount", "special fare", "early bird", "campaign",
    "fare", "reward", "redeem", "キャンペーン", "おトク", "割引", "特別", "セール",
)


def _matches(text: str, groups: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    lowered = compact_text(text).lower()
    return tuple(name for name, terms in groups.items() if any(term.lower() in lowered for term in terms))


def classify(text: str, airline: str) -> tuple[tuple[str, ...], tuple[str, ...], str]:
    origins = _matches(text, ORIGINS)
    destinations = _matches(text, DESTINATIONS)
    has_promo = any(term in compact_text(text).lower() for term in PROMO_TERMS)
    if origins and destinations:
        relevance = "high"
    elif origins or destinations:
        relevance = "medium"
    elif has_promo:
        relevance = "general"
    else:
        relevance = "low"

    # AirAsia/Scoot are useful mainly for the requested China-origin connection markets.
    if airline in {"AirAsia", "Scoot"} and origins and any(
        item in destinations for item in ("东南亚", "澳大利亚")
    ):
        relevance = "high"
    return origins, destinations, relevance
