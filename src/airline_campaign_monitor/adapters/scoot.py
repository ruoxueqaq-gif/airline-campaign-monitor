import json

from ..focus import classify
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
            origins, destinations, relevance = classify(f"{title} {summary}", self.airline)
            output.append(
                Campaign(
                    airline=self.airline,
                    title=title,
                    url=url,
                    summary=summary,
                    matched_origins=origins,
                    matched_destinations=destinations,
                    relevance=relevance,
                )
            )
        if not output:
            raise RuntimeError("官方 promotions API 可访问，但未提取到促销项目")
        return output
