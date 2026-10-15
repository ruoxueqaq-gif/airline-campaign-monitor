from datetime import date

from airline_campaign_monitor.deals import assess_deal, extract_dates, record_is_expired


def test_extracts_chinese_and_iso_dates():
    assert date(2026, 9, 27) in extract_dates("2026年9月1日至9月27日")
    assert date(2027, 8, 31) in extract_dates("2027-08-31")


def test_booking_deadline_controls_expiry():
    record = {
        "active": True,
        "booking_period": "销售至2026年9月10日 旅行期间：2026年10月1日至2027年3月1日",
    }
    assert record_is_expired(record, date(2026, 9, 21)) is True


def test_unstructured_historical_footnote_does_not_expire_ongoing_offer():
    record = {
        "active": True,
        "title": "日本国内转机航段票价免费",
        "summary": "长期活动；页面脚注提到2023年11月6日",
        "booking_period": "",
        "travel_period": "",
    }
    assert record_is_expired(record, date(2026, 9, 21)) is False


def test_large_discount_is_great_strength():
    result = assess_deal({"airline": "AirAsia", "title": "所有航班最高27%折扣", "summary": "Value Pack最高30%折扣"})
    assert result.strength == "GREAT"
    assert result.score >= 4
    assert result.flight_related is True


def test_non_flight_discount_is_not_a_best_fare():
    result = assess_deal({"airline": "Singapore Airlines", "title": "额外行李优惠", "summary": "Baggage allowance 15% off"})
    assert result.strength == "GREAT"
    assert result.flight_related is False



def test_expired_ana_sale_with_bad_old_booking_field_uses_labelled_summary():
    record = {
        "active": True,
        "title": "北美特惠",
        "booking_period": "再享最高300元立减优惠！",
        "summary": "上海出发北美特价 销售期间：销售至2024年8月31日 旅行期间：2024年9月1日至2024年9月27日",
    }
    assert record_is_expired(record, date(2026, 10, 15))


def test_future_ana_annual_sale_is_kept():
    record = {
        "active": True,
        "title": "ANA 11.11年度大促",
        "summary": "销售日期：2026年10月16日至2026年10月22日 旅行日期：2026年10月16日至2027年6月24日",
    }
    assert not record_is_expired(record, date(2026, 10, 15))
    assert record_is_expired(record, date(2026, 10, 23))
