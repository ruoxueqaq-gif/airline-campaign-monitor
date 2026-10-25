from ..focus import analyze
from ..models import Campaign, compact_text
from .base import BaseAdapter


class AirChinaAdapter(BaseAdapter):
    airline = "Air China"
    source_urls = (
        "https://www.airchina.com.cn/api/lego/page-data",
    )
    allowed_domains = ("airchina.com.cn", "act.airchina.com.cn", "webresource.airchina.com.cn")

    def fetch(self) -> list[Campaign]:
        payload = self.client.post_json(
            self.source_urls[0],
            {"parent_key": "PAGE_ID_CONF", "config_key": "LEGO_PAGE_ID_HOME_CONF", "locale": "zh-CN"},
        )
        output = []
        for template in payload.get("Data", {}).get("resultList", []):
            if template.get("templateType") != "airchina-index-activities":
                continue
            for item in template.get("templateData", {}).get("elementList", []):
                title = compact_text(str(item.get("title") or ""))
                summary = compact_text(str(item.get("describe") or ""))
                url = self._normalise_url(str(item.get("jumpUrl") or ""), "https://www.airchina.com.cn/zh-CN")
                text = f"{title} {summary}"
                ticket_related = any(term in text for term in ("特惠", "优惠", "畅飞", "航线", "直飞", "次卡", "机票"))
                if not title or not url or not self._allowed(url) or not ticket_related:
                    continue
                focus = analyze(text, self.airline)
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
            raise RuntimeError("官方首页活动 API 可访问，但未提取到促销项目")
        return output
