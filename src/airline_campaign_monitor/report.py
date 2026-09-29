from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import Change
from .display import AIRLINE_NAMES, DEAL_NAMES, RELEVANCE_NAMES, STATUS_NAMES, shown
from .focus import destination_priority


PROJECT_NAME = "airline-campaign-monitor"


def _snapshot(record: dict | None) -> str:
    if record is None:
        return "无（首次发现）"
    parts = [shown(record, "title") or "（无标题）"]
    if record.get("booking_period"):
        parts.append(f"购票期：{shown(record, 'booking_period')}")
    if record.get("travel_period"):
        parts.append(f"旅行期：{shown(record, 'travel_period')}")
    parts.append(f"相关度：{RELEVANCE_NAMES.get(record.get('relevance', 'LOW'), '低')}")
    parts.append(f"优惠力度：{DEAL_NAMES.get(record.get('deal_strength', 'NORMAL'), '普通')}")
    return "；".join(parts)


def render_report(changes: list[Change], *, detected_at: str | None = None) -> str:
    detected_at = detected_at or datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S %Z")
    counts = Counter(change.kind for change in changes)
    lines = [
        "# 航司促销活动更新",
        "",
        f"- 项目名称：`{PROJECT_NAME}`",
        f"- 检测时间：{detected_at}",
        f"- 变化汇总：新增 {counts['NEW']} / 更新 {counts['UPDATED']} / 结束 {counts['EXPIRED']}",
        "",
    ]
    for kind in ("NEW", "UPDATED", "EXPIRED"):
        selected = [change for change in changes if change.kind == kind]
        selected.sort(key=lambda change: destination_priority(change.campaign.get("destination_match") or change.campaign.get("matched_destinations") or []))
        if not selected:
            continue
        lines.extend([f"## {STATUS_NAMES[kind]}", ""])
        for change in selected:
            campaign = change.campaign
            before = _snapshot(change.previous)
            if kind == "EXPIRED":
                after = "连续两次未在成功抓取结果中出现（可能已结束）"
            else:
                after = _snapshot(campaign)
            lines.extend(
                [
                    f"### [{AIRLINE_NAMES.get(campaign.get('airline', ''), campaign.get('airline', ''))}] {shown(campaign, 'title')}",
                    "",
                    f"- 航空公司：{AIRLINE_NAMES.get(campaign.get('airline', ''), campaign.get('airline', ''))}",
                    f"- 出发地：{', '.join(campaign.get('origin_match') or campaign.get('matched_origins') or []) or '未命中'}",
                    f"- 目的地：{', '.join(campaign.get('destination_match') or campaign.get('matched_destinations') or []) or '未命中'}",
                    f"- 相关度：{RELEVANCE_NAMES.get(campaign.get('relevance', 'LOW'), '低')}",
                    f"- 优惠力度：{DEAL_NAMES.get(campaign.get('deal_strength', 'NORMAL'), '普通')}",
                    f"- 是否有明确价格：{'是' if campaign.get('has_explicit_price') else '否'}",
                    f"- 是否通知：{'是' if campaign.get('notify') else '否'}",
                    f"- 判断原因：{campaign.get('reason') or '无'}",
                    f"- 变化前：{before}",
                    f"- 变化后：{after}",
                    f"- 数据来源 URL：{campaign.get('url', '')}",
                ]
            )
            if kind == "EXPIRED":
                lines.append("- 人工复核提示：请打开来源 URL 确认活动是否确已结束或下架。")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_report(path: Path, changes: list[Change]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(changes), encoding="utf-8")
