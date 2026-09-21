from .base import BaseAdapter


class AnaAdapter(BaseAdapter):
    airline = "ANA"
    source_urls = ("https://www.ana.co.jp/zh/cn/",)
    allowed_domains = ("ana.co.jp", "aswbe.ana.co.jp")
    card_selectors = (".asw-layout-grid__item", ".cmp-teaser", ".mod-card", ".card", ".promotion", "article", "li")
