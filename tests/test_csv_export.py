from datetime import date, timedelta

from airline_campaign_monitor.csv_export import render_csv, save_csv_if_changed


def test_csv_is_excel_friendly_and_stable(tmp_path):
    booking_end = (date.today() + timedelta(days=7)).isoformat()
    state = {
        "schema_version": 1,
        "campaigns": {
            "id": {
                "airline": "ANA",
                "title": "上海出发日本特惠",
                "active": True,
                "relevance": "high",
                "matched_origins": ["上海"],
                "matched_destinations": ["日本"],
                "booking_period": f"2026-09-01 至 {booking_end}",
                "travel_period": "2026-10-01 至 2026-12-20",
                "first_seen": "2026-09-21",
                "last_changed": "2026-09-21",
                "url": "https://www.ana.co.jp/example",
                "summary": "含逗号,也能正常显示",
            }
        },
    }
    payload = render_csv(state)
    assert payload.startswith(b"\xef\xbb\xbf")
    assert "上海出发日本特惠" in payload.decode("utf-8-sig")

    path = tmp_path / "campaigns.csv"
    assert save_csv_if_changed(path, state) is True
    assert save_csv_if_changed(path, state) is False


def test_csv_omits_expired_and_best_deals_keeps_only_strong_offers():
    booking_end = (date.today() + timedelta(days=7)).isoformat()
    state = {
        "schema_version": 1,
        "campaigns": {
            "expired": {
                "airline": "ANA", "title": "旧活动", "active": True,
                "booking_period": "2025-01-01 至 2025-01-10", "url": "https://www.ana.co.jp/old",
            },
            "strong": {
                "airline": "AirAsia", "title": "所有航班最高27%折扣", "active": True,
                "booking_period": f"2026-09-01 至 {booking_end}", "url": "https://www.airasia.com/deal",
            },
            "normal": {
                "airline": "JAL", "title": "普通会员活动", "active": True,
                "url": "https://www.jal.co.jp/deal",
            },
        },
    }
    regular = render_csv(state).decode("utf-8-sig")
    best = render_csv(state, best_only=True).decode("utf-8-sig")
    assert "旧活动" not in regular
    assert "所有航班最高27%折扣" in regular
    assert "所有航班最高27%折扣" in best
    assert "普通会员活动" not in best



def test_high_priority_low_starting_fare_gets_featured():
    from datetime import date
    today = date.today()
    booking_end = (today + timedelta(days=7)).isoformat()
    state = {"schema_version": 1, "campaigns": {"sale": {
        "airline": "ANA",
        "title": "ANA 11.11年度大促",
        "summary": "中国出发日本经济舱往返680元起",
        "booking_period": f"{today.isoformat()} 至 {booking_end}",
        "active": True,
        "relevance": "HIGH",
        "has_explicit_price": True,
        "has_promotion": True,
        "url": "https://www.ana.co.jp/zh/cn/plan-book/promotions/2026-1111-cpn/",
    }}}
    best = render_csv(state, best_only=True).decode("utf-8-sig")
    assert "ANA 11.11年度大促" in best
