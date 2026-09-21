from airline_campaign_monitor.models import Campaign
from airline_campaign_monitor.state import empty_state, reconcile


def campaign(title="上海飞东京限时特惠", booking="2026-09-01 至 2026-09-10"):
    return Campaign(
        airline="ANA",
        title=title,
        url="https://www.ana.co.jp/zh/cn/plan-book/promotions/test",
        booking_period=booking,
        matched_origins=("上海",),
        matched_destinations=("日本",),
        relevance="high",
    )


def test_new_campaign_is_detected():
    state, changes = reconcile(empty_state(), [campaign()], {"ANA"}, today="2026-09-01")
    assert [item.kind for item in changes] == ["NEW"]
    assert len(state["campaigns"]) == 1


def test_date_change_is_updated():
    first_state, _ = reconcile(empty_state(), [campaign()], {"ANA"}, today="2026-09-01")
    second_state, changes = reconcile(
        first_state,
        [campaign(booking="2026-09-01 至 2026-09-20")],
        {"ANA"},
        today="2026-09-02",
    )
    assert [item.kind for item in changes] == ["UPDATED"]
    record = next(iter(second_state["campaigns"].values()))
    assert record["booking_period"].endswith("09-20")


def test_expired_requires_two_successful_missing_runs():
    state, _ = reconcile(empty_state(), [campaign()], {"ANA"}, today="2026-09-01")
    state, changes = reconcile(state, [], {"ANA"}, today="2026-09-02")
    assert changes == []
    state, changes = reconcile(state, [], {"ANA"}, today="2026-09-03")
    assert [item.kind for item in changes] == ["EXPIRED"]
    assert state["campaigns"] == {}


def test_explicitly_past_campaign_is_not_saved():
    state, changes = reconcile(empty_state(), [campaign(booking="2025-01-01 至 2025-01-10")], {"ANA"}, today="2026-09-21")
    assert state["campaigns"] == {}
    assert changes == []


def test_failed_airline_is_not_marked_missing():
    state, _ = reconcile(empty_state(), [campaign()], {"ANA"}, today="2026-09-01")
    next_state, changes = reconcile(state, [], set(), today="2026-09-02")
    assert changes == []
    assert next_state == state
