import json

from ..focus import analyze
from ..models import Campaign, compact_text
from .base import BaseAdapter


class ScootAdapter(BaseAdapter):
    airline = "Scoot"
    source_urls = (
        "https://www.flyscoot.com/api/flyscoot/promotionstiles?sf_culture=zh",
    )
    allowed_domains = ("flyscoot.com",)

    def fetch(self) -> list[Campaign]:
        payload = json.loads(self.client.get_text(self.source_urls[0]))
        output = []
        for item in payload.get("value", []):
            title = compact_text(str(item.get("Title") or item.get("Key") or ""))
            summary = compact_text(str(item.get("Text") or item.get("SubText") or ""))
            url = self._normalise_url(str(item.get("LinkUrl") or item.get("ItemDefaultUrl") or ""), self.source_urls[0])
            if not title or not url or not self._allowed(url) or not self._looks_promotional(f"{title} {summary}"):
                continue
            focus = analyze(f"{title} {summary}", self.airline)
            output.append(
                Campaign(
                    airline=self.airline,
                    title=title,
                    url=url,
                    summary=summary,
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
            )
        if not output:
            raise RuntimeError("官方 promotions API 可访问，但未提取到促销项目")
        return output
