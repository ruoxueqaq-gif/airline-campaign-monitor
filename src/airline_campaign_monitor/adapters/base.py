from __future__ import annotations

from abc import ABC
import re
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup, Tag

from ..focus import PROMO_TERMS, classify
from ..http import HttpClient
from ..models import Campaign, compact_text

DATE_RANGE_PATTERNS = (
    re.compile(r"(?:销售|购票|预订|出票)(?:日期|期间|时间|期限)?[：:]?\s*([^。；\n]{4,100})", re.I),
    re.compile(r"(?:book(?:ing)?|sale)\s+(?:period|dates?)?[：:]?\s*([^.;\n]{4,100})", re.I),
)
TRAVEL_RANGE_PATTERNS = (
    re.compile(r"(?:旅行|出行|搭乘|适用|飞行)(?:日期|期间|时间|期限)?[：:]?\s*([^。；\n]{4,100})", re.I),
    re.compile(r"travel\s+(?:period|dates?)?[：:]?\s*([^.;\n]{4,100})", re.I),
)


class BaseAdapter(ABC):
    airline: str
    source_urls: tuple[str, ...]
    allowed_domains: tuple[str, ...]
    card_selectors: tuple[str, ...] = (
        "article",
        ".campaign",
        ".promotion",
        ".offer",
        ".card",
        ".cmp-teaser",
        "li",
    )
    max_campaigns = 80

    def __init__(self, client: HttpClient | None = None) -> None:
        self.client = client or HttpClient()

    def fetch(self) -> list[Campaign]:
        campaigns: dict[str, Campaign] = {}
        errors: list[str] = []
        for source_url in self.source_urls:
            try:
                html = self.client.get_text(source_url)
                for campaign in self.parse(html, source_url):
                    campaigns[campaign.campaign_id] = campaign
            except Exception as exc:  # each URL gets a chance; adapter fails only if all fail
                errors.append(f"{source_url}: {exc}")
        if not campaigns:
            detail = "; ".join(errors) if errors else "页面可访问，但未提取到结构化促销卡片"
            raise RuntimeError(detail)
        return list(campaigns.values())[: self.max_campaigns]

    def parse(self, html: str, source_url: str) -> list[Campaign]:
        soup = BeautifulSoup(html, "html.parser")
        nodes: list[Tag] = []
        for selector in self.card_selectors:
            nodes.extend(node for node in soup.select(selector) if isinstance(node, Tag))
        nodes.extend(node for node in soup.select("h1, h2, h3, h4") if isinstance(node, Tag))

        output: dict[str, Campaign] = {}
        for node in nodes:
            campaign = self._campaign_from_node(node, source_url)
            if campaign:
                existing = output.get(campaign.campaign_id)
                if existing is None or self._quality(campaign) > self._quality(existing):
                    output[campaign.campaign_id] = campaign
        return list(output.values())

    def _campaign_from_node(self, node: Tag, source_url: str) -> Campaign | None:
        title_node = node if node.name in {"h1", "h2", "h3", "h4"} else node.select_one(
            "h1, h2, h3, h4, .title, .heading, .ds-linkList__heading, [data-content-field='title']"
        )
        link = title_node if isinstance(title_node, Tag) and title_node.name == "a" and title_node.get("href") else None
        link = link or (node if node.name == "a" else node.find("a", href=True))
        if not isinstance(link, Tag):
            parent_link = node.find_parent("a", href=True)
            link = parent_link if isinstance(parent_link, Tag) else None
        if not link or not link.get("href"):
            return None

        title = compact_text(title_node.get_text(" ", strip=True) if title_node else link.get_text(" ", strip=True))
        body = compact_text(node.get_text(" ", strip=True))
        if len(title) < 5 or len(title) > 240 or not self._looks_promotional(f"{title} {body}"):
            return None

        url = self._normalise_url(str(link.get("href")), source_url)
        if not url or not self._allowed(url):
            return None
        summary = body[:800]
        origins, destinations, relevance = classify(f"{title} {summary}", self.airline)
        return Campaign(
            airline=self.airline,
            title=title,
            url=url,
            summary=summary,
            booking_period=self._extract_period(summary, DATE_RANGE_PATTERNS),
            travel_period=self._extract_period(summary, TRAVEL_RANGE_PATTERNS),
            matched_origins=origins,
            matched_destinations=destinations,
            relevance=relevance,
        )

    @staticmethod
    def _looks_promotional(text: str) -> bool:
        lowered = compact_text(text).lower()
        return any(term in lowered for term in PROMO_TERMS)

    def _allowed(self, url: str) -> bool:
        hostname = (urlparse(url).hostname or "").lower()
        return any(hostname == domain or hostname.endswith(f".{domain}") for domain in self.allowed_domains)

    @staticmethod
    def _normalise_url(href: str, source_url: str) -> str:
        if href.startswith(("javascript:", "mailto:", "tel:", "#")):
            return ""
        parsed = urlparse(urljoin(source_url, href))
        return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/") or "/", "", parsed.query, ""))

    @staticmethod
    def _extract_period(text: str, patterns: tuple[re.Pattern[str], ...]) -> str:
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return compact_text(match.group(1))[:160]
        return ""

    @staticmethod
    def _quality(campaign: Campaign) -> int:
        return len(campaign.summary) + 200 * bool(campaign.booking_period) + 200 * bool(campaign.travel_period)
