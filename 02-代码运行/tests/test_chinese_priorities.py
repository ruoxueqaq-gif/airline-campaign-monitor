from unittest.mock import patch

from airline_campaign_monitor.csv_export import render_csv
from airline_campaign_monitor.display import display_text
from airline_campaign_monitor.focus import analyze, destination_priority
from airline_campaign_monitor.models import Campaign
from airline_campaign_monitor.report import render_report
from airline_campaign_monitor.state import empty_state, reconcile


class TranslationResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return [[["泰国机票限时促销", None]]]


def test_destination_priority_affects_relevance():
    cases = [
        analyze(f"杭州出发飞往{place}机票限时促销 ¥1000", "ANA")
        for place in ("日本", "泰国曼谷", "澳大利亚", "英国伦敦", "美国")
    ]
    assert [item.relevance for item in cases] == ["HIGH", "HIGH", "MEDIUM", "MEDIUM", "LOW"]
    assert [destination_priority(item.destinations) for item in cases] == [0, 0, 1, 1, 3]
    assert "越南" in analyze("杭州出发飞往胡志明机票优惠", "Vietnam Airlines").destinations


def test_chinese_display_does_not_trigger_source_update():
    campaign = Campaign(
        "AirAsia", "Thailand flight sale", "https://airasia.com/sale",
        "Save 25% on flights", matched_origins=("HGH",),
        matched_destinations=("泰国", "东南亚"), relevance="HIGH",
    )
    with patch("airline_campaign_monitor.display.requests.get", return_value=TranslationResponse()):
        state, changes = reconcile(empty_state(), [campaign], {"AirAsia"}, today="2026-09-29")
        next_state, next_changes = reconcile(state, [campaign], {"AirAsia"}, today="2026-09-30")
    assert next_changes == []
    assert next_state == state
    assert "泰国机票限时促销" in render_csv(state).decode("utf-8-sig")
    assert "Thailand flight sale" not in render_csv(state).decode("utf-8-sig")
    assert "泰国机票限时促销" in render_report(changes, detected_at="2026-09-29")


def test_translation_failure_keeps_display_in_chinese():
    import requests
    with patch("airline_campaign_monitor.display.requests.get", side_effect=requests.Timeout()):
        shown, pending = display_text("Japanese fare sale", "title")
    assert shown == "促销活动（中文翻译暂不可用）"
    assert pending
