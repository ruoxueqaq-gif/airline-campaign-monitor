from datetime import date

from airline_campaign_monitor.adapters.ana import AnaAdapter
from airline_campaign_monitor.adapters.jal import JalAdapter
from airline_campaign_monitor.deals import record_is_expired
from airline_campaign_monitor.focus import analyze


def test_ana_china_1111_image_banner_triggers_notification():
    html = """
    <div class="hero">
      <a href="/zh/cn/plan-book/promotions/2026-1111-cpn/">
        <img alt="ANA 11.11年度大促" src="/banner.webp">
      </a>
    </div>
    """
    campaigns = AnaAdapter().parse(html, "https://www.ana.co.jp/zh/cn/")
    assert len(campaigns) == 1
    assert campaigns[0].title == "ANA 11.11年度大促"
    assert campaigns[0].relevance == "HIGH"
    assert campaigns[0].notify is True


def test_jal_chinese_market_annual_banner_notifies():
    html = """
    <a href="/zh-cn/2026-sale">
      <img alt="JAL 双十一限时优惠" src="sale.webp">
    </a>
    """
    campaigns = JalAdapter().parse(html, "https://www.jal.co.jp/zh-cn/")
    assert len(campaigns) == 1
    assert campaigns[0].relevance == "HIGH"
    assert campaigns[0].notify is True


def test_japanese_only_black_friday_not_marked_high():
    result = analyze(
        "日本出发 Black Friday 国际机票优惠 东京飞檀香山",
        "JAL",
        headline="Black Friday 国际机票优惠",
        china_market=False,
    )
    assert result.relevance == "LOW"
    assert result.notify is False


def test_old_annual_sale_footnote_does_not_trigger_special_alert():
    result = analyze(
        "日本国内转机航段免费，2023年11.11促销详情在旧页面",
        "ANA",
        headline="日本国内转机航段免费",
        china_market=True,
    )
    assert result.relevance != "HIGH"
    assert result.notify is False


def test_japanese_booking_period_excludes_travel_period():
    html = """
    <div class="ds-linkList__item">
      <a href="/jp/ja/inter/special/sale/">
        <h2>JAL海外航空券タイムセール</h2>
        販売期間：2026年10月8日（木）00:00～10月18日（日）23:59
        搭乗期間：2026年10月8日（木）～2027年7月31日（土）
      </a>
    </div>
    """
    campaigns = JalAdapter().parse(html, "https://www.jal.co.jp/ja-jp/campaign/inter.html")
    assert len(campaigns) == 1
    item = campaigns[0]
    assert "2026年10月8日" in item.booking_period
    assert "2027年" not in item.booking_period
    assert "2027年7月31日" in item.travel_period
    assert record_is_expired(item.to_record("2026-10-10"), date(2026, 10, 20))



class StubAnaClient:
    def __init__(self, pages):
        self.pages = pages

    def get_text(self, url):
        if url not in self.pages:
            raise RuntimeError("source unavailable")
        return self.pages[url]


def test_ana_home_unlinked_current_year_hero_creates_high_priority_campaign():
    from datetime import date
    year = date.today().year
    html = f'<div class="hero"><img alt="11.11年度大促" src="/www2/zh/cn/top/{year}-1111-cpn_hero_cn_pc.jpg"></div>'
    found = AnaAdapter().parse(html, "https://www.ana.co.jp/zh/cn/")
    assert len(found) == 1
    assert found[0].url == AnaAdapter.annual_url(year)
    assert found[0].relevance == "HIGH"
    assert found[0].notify is True


def test_ana_annual_sale_detail_independent_of_homepage_card():
    from datetime import date
    year = date.today().year
    url = AnaAdapter.annual_url(year)
    detail_html = f"""
    <html><head><title>全日空航空ANA 11.11年度大促</title></head><body>
      <main><h1>全日空航空ANA 11.11年度大促</h1>
        北京、上海浦东、杭州出发飞往日本各地，
        中日经济舱往返680元起！
        销售日期：{year}年10月16日至{year}年10月22日
        旅行日期：{year}年10月16日至{year+1}年6月24日
      </main>
    </body></html>"""
    homepage = "<html><body>暂无横幅</body></html>"
    promotions = '<article><a href="/zh/cn/other"><h2>ANA限时优惠活动</h2></a></article>'
    client = StubAnaClient({
        "https://www.ana.co.jp/zh/cn/": homepage,
        "https://www.ana.co.jp/zh/cn/plan-book/promotions/": promotions,
        url: detail_html,
    })
    found = AnaAdapter(client).fetch()
    annual = next(c for c in found if c.url == url)
    assert annual.relevance == "HIGH"
    assert annual.notify
    assert annual.has_explicit_price
    assert str(year) in annual.booking_period
    assert str(year+1) in annual.travel_period


def test_ana_historical_footnote_cannot_create_current_year_campaign():
    html = '<article><a href="/zh/cn/japan"><h2>日本国内航段免费</h2><p>2023年全日空11.11即将推出</p></a></article>'
    found = AnaAdapter().parse(html, "https://www.ana.co.jp/zh/cn/")
    assert all("1111-cpn" not in c.url for c in found)
