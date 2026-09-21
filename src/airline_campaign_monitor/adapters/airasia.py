from .base import BaseAdapter


class AirAsiaAdapter(BaseAdapter):
    airline = "AirAsia"
    source_urls = (
        "https://newsroom.airasia.com/news",
        "https://www.airasia.com/zh/cn",
    )
    allowed_domains = ("airasia.com",)
    card_selectors = ("article", ".summary-item", ".card", ".promotion", ".deal", "li")

