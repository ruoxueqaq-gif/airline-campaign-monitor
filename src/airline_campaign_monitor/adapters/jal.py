from .base import BaseAdapter


class JalAdapter(BaseAdapter):
    airline = "JAL"
    source_urls = (
        "https://www.jal.co.jp/ja-jp/campaign/inter.html",
        "https://www.jal.co.jp/jp/ja/inter/fare/special_fare/",
    )
    allowed_domains = ("jal.co.jp",)
    card_selectors = (".ds-linkList__item",)
