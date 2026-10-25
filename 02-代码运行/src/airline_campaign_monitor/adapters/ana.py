"""ANA official promotions, including unlinked annual sale hero banners."""
from __future__ import annotations
from datetime import date
import re
from bs4 import BeautifulSoup
from .base import BaseAdapter, DATE_RANGE_PATTERNS, TRAVEL_RANGE_PATTERNS
from ..focus import analyze
from ..models import Campaign, compact_text

ANNUAL_BANNER = re.compile(r"(20\d{2})-1111-cpn", re.I)
ANNUAL_TEXT = re.compile(r"11[.·]11|双\s*11|双\s*十\s*一", re.I)


class AnaAdapter(BaseAdapter):
    airline = "ANA"
    source_urls = (
        "https://www.ana.co.jp/zh/cn/",
        "https://www.ana.co.jp/zh/cn/plan-book/promotions/",
    )
    allowed_domains = ("ana.co.jp", "aswbe.ana.co.jp")
    card_selectors = (".asw-layout-grid__item", ".cmp-teaser", ".mod-card", ".card", ".promotion", "article", "li")

    @staticmethod
    def annual_url(year: int) -> str:
        return f"https://www.ana.co.jp/zh/cn/plan-book/promotions/{year}-1111-cpn/"

    def parse(self, html: str, source_url: str) -> list[Campaign]:
        found = {campaign.campaign_id: campaign for campaign in super().parse(html, source_url)}
        # ANA homepage hero images may have no clickable <a href>. The image
        # filename is the source of the promotion year; ignore old footnotes.
        if source_url.rstrip("/") == "https://www.ana.co.jp/zh/cn":
            soup = BeautifulSoup(html, "html.parser")
            for img in soup.find_all("img"):
                image_src = " ".join(str(img.get(attr) or "") for attr in (
                    "src", "data-src", "srcset", "data-srcset", "data-original",
                ))
                match = ANNUAL_BANNER.search(image_src)
                alt = compact_text(str(img.get("alt") or ""))
                if not match or int(match.group(1)) != date.today().year or not ANNUAL_TEXT.search(alt):
                    continue
                year = int(match.group(1))
                title = f"ANA {year} 11.11年度大促"
                focus = analyze(title, "ANA", headline=title, china_market=True)
                item = Campaign(
                    airline="ANA", title=title, url=self.annual_url(year),
                    summary=f"{title}（ANA中国官网首页官方活动横幅；详情页待核对）",
                    matched_origins=focus.origins, matched_destinations=focus.destinations,
                    relevance=focus.relevance, deal_strength=focus.deal_strength,
                    has_explicit_price=focus.explicit_price, has_promotion=focus.promotion,
                    core_route_change=focus.core_route_change, notify=focus.notify,
                    reason=focus.reason, relevance_score=focus.score,
                )
                found[item.campaign_id] = item
        return list(found.values())

    def _annual_detail(self, html: str, url: str, year: int) -> Campaign | None:
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.find("h1") or soup.title
        title = compact_text(heading.get_text(" ", strip=True)) if heading else ""
        main = soup.select_one("main") or soup.body or soup
        full = compact_text(main.get_text(" ", strip=True))
        if not ANNUAL_TEXT.search(title) or str(year) not in full[:2500]:
            return None
        summary = full[:3000]
        focus = analyze(f"{title} {summary}", "ANA", headline=title, china_market=True)
        return Campaign(
            airline="ANA", title=title, url=url, summary=summary,
            booking_period=self._extract_period(summary, DATE_RANGE_PATTERNS),
            travel_period=self._extract_period(summary, TRAVEL_RANGE_PATTERNS),
            matched_origins=focus.origins, matched_destinations=focus.destinations,
            relevance=focus.relevance, deal_strength=focus.deal_strength,
            has_explicit_price=focus.explicit_price, has_promotion=focus.promotion,
            core_route_change=focus.core_route_change, notify=focus.notify,
            reason=focus.reason, relevance_score=focus.score,
        )

    def fetch(self) -> list[Campaign]:
        found = {campaign.campaign_id: campaign for campaign in super().fetch()}
        today = date.today()
        if today.month in (9, 10, 11, 12):
            url = self.annual_url(today.year)
            try:
                detail = self._annual_detail(self.client.get_text(url), url, today.year)
                if detail:
                    found[detail.campaign_id] = detail
            except Exception as exc:
                if any(c.url == url for c in found.values()):
                    print(f"[WARN] ANA: 年度促销详情不可访问，保留官网横幅记录: {exc}")
        return list(found.values())[:self.max_campaigns]
