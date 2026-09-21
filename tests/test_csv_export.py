from airline_campaign_monitor.csv_export import render_csv, save_csv_if_changed


def test_csv_is_excel_friendly_and_stable(tmp_path):
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
                "booking_period": "2026-09-01 至 2026-09-30",
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
