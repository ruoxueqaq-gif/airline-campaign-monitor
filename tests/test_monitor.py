import json

from airline_campaign_monitor import monitor
from airline_campaign_monitor.models import Campaign


def item(title: str, url: str, booking: str = "") -> Campaign:
    return Campaign(
        airline="Test Air",
        title=title,
        url=url,
        booking_period=booking,
        matched_origins=("上海",),
        matched_destinations=("东南亚",),
        relevance="HIGH",
        deal_strength="GOOD",
        has_promotion=True,
        notify=True,
        reason="核心出发地 PVG/SHA + 东南亚目的地 + 明确促销活动",
    )


class BaselineAdapter:
    airline = "Test Air"

    def __init__(self, _client):
        pass

    def fetch(self):
        return [item("上海飞新加坡促销", "https://example.test/old")]


def test_first_run_builds_baseline_without_report(tmp_path, monkeypatch):
    state_path = tmp_path / "campaigns.json"
    csv_path = tmp_path / "csv" / "my_campaigns.csv"
    report_path = tmp_path / "change.md"
    monkeypatch.setattr(monitor, "ALL_ADAPTERS", (BaselineAdapter,))

    assert monitor.run(state_path, report_path) == 0
    assert state_path.exists()
    assert csv_path.exists()
    assert not report_path.exists()
    assert len(json.loads(state_path.read_text(encoding="utf-8"))["campaigns"]) == 1
    csv_text = csv_path.read_text(encoding="utf-8-sig")
    assert "航空公司,促销标题,状态" in csv_text
    assert "Test Air,上海飞新加坡促销,ACTIVE" in csv_text


def test_new_campaign_creates_new_report(tmp_path, monkeypatch):
    state_path = tmp_path / "campaigns.json"
    report_path = tmp_path / "change.md"
    monkeypatch.setattr(monitor, "ALL_ADAPTERS", (BaselineAdapter,))
    monitor.run(state_path, report_path)

    class WithNew(BaselineAdapter):
        def fetch(self):
            return super().fetch() + [item("上海飞曼谷限时优惠", "https://example.test/new")]

    monkeypatch.setattr(monitor, "ALL_ADAPTERS", (WithNew,))
    assert monitor.run(state_path, report_path) == 0
    assert "## NEW" in report_path.read_text(encoding="utf-8")
    assert "上海飞曼谷限时优惠" in report_path.read_text(encoding="utf-8")

    # The persisted campaign ID/content prevents the next identical run from
    # generating the same Issue payload again.
    assert monitor.run(state_path, report_path) == 0
    assert not report_path.exists()


def test_booking_date_change_creates_updated_report(tmp_path, monkeypatch):
    state_path = tmp_path / "campaigns.json"
    report_path = tmp_path / "change.md"

    class First(BaselineAdapter):
        def fetch(self):
            return [item("上海飞新加坡促销", "https://example.test/same", "至 9 月 10 日")]

    class Changed(BaselineAdapter):
        def fetch(self):
            return [item("上海飞新加坡促销", "https://example.test/same", "延长至 9 月 20 日")]

    monkeypatch.setattr(monitor, "ALL_ADAPTERS", (First,))
    monitor.run(state_path, report_path)
    monkeypatch.setattr(monitor, "ALL_ADAPTERS", (Changed,))
    monitor.run(state_path, report_path)
    assert "## UPDATED" in report_path.read_text(encoding="utf-8")
    assert "延长至 9 月 20 日" in report_path.read_text(encoding="utf-8")


def test_one_adapter_failure_does_not_block_others(tmp_path, monkeypatch):
    state_path = tmp_path / "campaigns.json"
    report_path = tmp_path / "change.md"
    monkeypatch.setattr(monitor, "ALL_ADAPTERS", (BaselineAdapter,))
    monitor.run(state_path, report_path)

    class Broken:
        airline = "Broken Air"

        def __init__(self, _client):
            pass

        def fetch(self):
            raise RuntimeError("simulated timeout")

    class Good(BaselineAdapter):
        def fetch(self):
            return super().fetch() + [item("上海飞悉尼促销", "https://example.test/sydney")]

    monkeypatch.setattr(monitor, "ALL_ADAPTERS", (Broken, Good))
    assert monitor.run(state_path, report_path) == 0
    report = report_path.read_text(encoding="utf-8")
    assert "上海飞悉尼促销" in report
    assert "Broken Air" not in report


def test_low_relevance_change_is_recorded_without_issue_report(tmp_path, monkeypatch):
    state_path = tmp_path / "campaigns.json"
    report_path = tmp_path / "change.md"
    monkeypatch.setattr(monitor, "ALL_ADAPTERS", (BaselineAdapter,))
    monitor.run(state_path, report_path)

    class WithLowNews(BaselineAdapter):
        def fetch(self):
            low = Campaign(
                airline="AirAsia",
                title="Don Mueang international expansion",
                url="https://example.test/pr-news",
                matched_destinations=("东南亚",),
                relevance="LOW",
                deal_strength="NORMAL",
                notify=False,
                reason="仅境外航线变化",
            )
            return super().fetch() + [low]

    monkeypatch.setattr(monitor, "ALL_ADAPTERS", (WithLowNews,))
    assert monitor.run(state_path, report_path) == 0
    assert not report_path.exists()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert any(record["title"] == "Don Mueang international expansion" for record in state["campaigns"].values())
