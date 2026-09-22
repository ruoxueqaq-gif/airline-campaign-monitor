from airline_campaign_monitor.focus import analyze


def test_airasia_foreign_capacity_pr_is_low_and_silent():
    result = analyze(
        "AirAsia Gears Up for High Season with Major International Expansion, "
        "Offering Direct Flights from Don Mueang to 46 Cities Across 53 Routes in Southeast Asia and Japan",
        "AirAsia",
    )
    assert result.origins == ()
    assert set(result.destinations) == {"日本", "东南亚"}
    assert result.relevance == "LOW"
    assert result.deal_strength == "NORMAL"
    assert result.explicit_price is False
    assert result.notify is False


def test_core_origin_explicit_price_is_high_and_notified():
    result = analyze("上海浦东出发飞悉尼特价，机票 ¥699 起", "AirAsia")
    assert result.origins == ("PVG",)
    assert "澳大利亚" in result.destinations
    assert result.relevance == "HIGH"
    assert result.deal_strength == "GOOD"
    assert result.explicit_price is True
    assert result.notify is True


def test_core_route_resumption_is_high_and_notified():
    result = analyze("杭州—大阪航线复航", "ANA")
    assert result.origins == ("HGH",)
    assert result.relevance == "HIGH"
    assert result.core_route_change is True
    assert result.notify is True


def test_secondary_origin_sale_is_medium_and_notified():
    result = analyze("南京出发日本航线限时促销", "JAL")
    assert result.origins == ("NKG",)
    assert result.relevance == "MEDIUM"
    assert result.notify is True


def test_destination_alone_cannot_raise_relevance():
    result = analyze("东南亚及日本目的地网络持续扩展", "AirAsia")
    assert result.relevance == "LOW"
    assert result.notify is False


def test_explicit_discount_from_core_origin_is_notified():
    result = analyze("杭州出发日本航线限时 7 折", "ANA")
    assert result.relevance == "HIGH"
    assert result.deal_strength == "GREAT"
    assert result.promotion is True
    assert result.notify is True
