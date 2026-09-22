import json

from bs4 import BeautifulSoup

from ..focus import analyze
from ..models import Campaign, compact_text
from .base import BaseAdapter


class VietnamAirlinesAdapter(BaseAdapter):
    airline = "Vietnam Airlines"
    source_urls = (
        "https://www.vietnamairlines.com/zh/monthly-offers",
    )
    allowed_domains = ("vietnamairlines.com",)

    def fetch(self) -> list[Campaign]:
        soup = BeautifulSoup(self.client.get_text(self.source_urls[0]), "html.parser")
        output: dict[str, Campaign] = {}
        for node in soup.select(".cmp-promotion-list[data-promotion]"):
            payload = json.loads(node.get("data-promotion", "{}"))
            for item in payload.get("promotionList", []):
                title = compact_text(str(item.get("title") or ""))
                summary = compact_text(str(item.get("shortDescription") or ""))
                url = self._normalise_url(str(item.get("ctaDirect") or ""), self.source_urls[0])
                if not title or not url or not self._allowed(url) or not self._looks_promotional(f"{title} {summary}"):
                    continue
                focus = analyze(f"{title} {summary}", self.airline)
                start = str(item.get("effectiveStartDate") or "")[:10]
                end = str(item.get("effectiveEndDate") or "")[:10]
                campaign = Campaign(
                    airline=self.airline,
                    title=title,
                    url=url,
                    summary=summary,
                    booking_period=" 至 ".join(value for value in (start, end) if value),
                    matched_origins=focus.origins,
                    matched_destinations=focus.destinations,
                    relevance=focus.relevance,
                    deal_strength=focus.deal_strength,
                    has_explicit_price=focus.explicit_price,
                    has_promotion=focus.promotion,
                    core_route_change=focus.core_route_change,
                    notify=focus.notify,
                    reason=focus.reason,
                    relevance_score=focus.score,
                )
                output[campaign.campaign_id] = campaign
        if not output:
            raise RuntimeError("官方优惠列表可访问，但未提取到促销项目")
        return list(output.values())
