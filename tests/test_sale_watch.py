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
