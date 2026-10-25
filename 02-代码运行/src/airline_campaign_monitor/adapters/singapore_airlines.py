from .base import BaseAdapter


class SingaporeAirlinesAdapter(BaseAdapter):
    airline = "Singapore Airlines"
    source_urls = (
        "https://www.singaporeair.com/en_UK/cn/plan-travel/local-promotions/local-promotion-in-china/",
    )
    allowed_domains = ("singaporeair.com",)
    card_selectors = ("article", ".card", ".promotion", ".offer", ".cmp-teaser", "li")

