from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import Change


PROJECT_NAME = "airline-campaign-monitor"


def _snapshot(record: dict | None) -> str:
    if record is None:
        return "无（首次发现）"
    parts = [str(record.get("title") or "（无标题）")]
    if record.get("booking_period"):
        parts.append(f"购票期：{record['booking_period']}")
    if record.get("travel_period"):
        parts.append(f"旅行期：{record['travel_period']}")
    parts.append(f"相关度：{record.get('relevance', 'LOW')}")
    parts.append(f"优惠力度：{record.get('deal_strength', 'NORMAL')}")
    return "；".join(parts)


def render_report(changes: list[Change], *, detected_at: str | None = None) -> str:
    detected_at = detected_at or datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S %Z")
    counts = Counter(change.kind for change in changes)
    lines = [
        "# 航司促销活动更新",
        "",
        f"- 项目名称：`{PROJECT_NAME}`",
        f"- 检测时间：{detected_at}",
        f"- 变化汇总：NEW {counts['NEW']} / UPDATED {counts['UPDATED']} / EXPIRED {counts['EXPIRED']}",
        "",
    ]
    for kind in ("NEW", "UPDATED", "EXPIRED"):
        selected = [change for change in changes if change.kind == kind]
        if not selected:
            continue
        lines.extend([f"## {kind}", ""])
        for change in selected:
            campaign = change.campaign
            before = _snapshot(change.previous)
            if kind == "EXPIRED":
                after = "连续两次未在成功抓取结果中出现（可能已结束）"
            else:
                after = _snapshot(campaign)
            lines.extend(
                [
                    f"### [{campaign.get('airline', '')}] {campaign.get('title', '')}",
                    "",
                    f"- 航空公司：{campaign.get('airline', '')}",
                    f"- 出发地：{', '.join(campaign.get('origin_match') or campaign.get('matched_origins') or []) or '未命中'}",
                    f"- 目的地：{', '.join(campaign.get('destination_match') or campaign.get('matched_destinations') or []) or '未命中'}",
                    f"- 相关度：{campaign.get('relevance', 'LOW')}",
                    f"- 优惠力度：{campaign.get('deal_strength', 'NORMAL')}",
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
