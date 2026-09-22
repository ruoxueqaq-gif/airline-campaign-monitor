from airline_campaign_monitor.models import Change
from airline_campaign_monitor.report import render_report


def test_issue_report_contains_required_audit_fields():
    campaign = {
        "airline": "AirAsia",
        "title": "上海浦东出发飞悉尼特价 ¥699 起",
        "url": "https://example.test/deal",
        "origin_match": ["PVG"],
        "destination_match": ["澳大利亚"],
        "relevance": "HIGH",
        "deal_strength": "GOOD",
        "has_explicit_price": True,
        "notify": True,
        "reason": "核心出发地 PVG + 澳大利亚目的地 + 明确促销价格",
    }
    report = render_report([Change("NEW", campaign)], detected_at="2026-09-23 09:20:00 CST")
    for expected in (
        "检测时间", "变化前", "变化后", "数据来源 URL", "项目名称",
        "航空公司", "出发地", "目的地", "相关度", "优惠力度", "是否有明确价格", "是否通知", "判断原因",
    ):
        assert expected in report
