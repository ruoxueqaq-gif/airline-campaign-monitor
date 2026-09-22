from airline_campaign_monitor.adapters.ana import AnaAdapter


def test_adapter_extracts_structured_campaign():
    html = """
    <article>
      <a href="/zh/cn/plan-book/promotions/sale">
        <h2>上海出发日本限时特惠</h2>
        <p>购票日期：2026年9月1日至9月10日；旅行日期：2026年10月1日至12月20日。</p>
      </a>
    </article>
    """
    campaigns = AnaAdapter().parse(html, "https://www.ana.co.jp/zh/cn/")
    assert len(campaigns) == 1
    assert campaigns[0].matched_origins == ("PVG", "SHA")
    assert campaigns[0].matched_destinations == ("日本",)
    assert campaigns[0].booking_period.startswith("2026年9月1日")
    assert campaigns[0].travel_period.startswith("2026年10月1日")
    assert campaigns[0].relevance == "HIGH"
    assert campaigns[0].notify is True


def test_adapter_rejects_non_official_link():
    html = '<article><a href="https://third-party.example/deal"><h2>上海飞日本促销</h2></a></article>'
    assert AnaAdapter().parse(html, "https://www.ana.co.jp/zh/cn/") == []


def test_adapter_keeps_core_route_resumption_without_sale_word():
    html = """
    <article>
      <a href="/zh/cn/plan-book/promotions/resume-osaka">
        <h2>杭州—大阪航线复航</h2>
      </a>
    </article>
    """
    campaigns = AnaAdapter().parse(html, "https://www.ana.co.jp/zh/cn/")
    assert len(campaigns) == 1
    assert campaigns[0].core_route_change is True
    assert campaigns[0].notify is True

