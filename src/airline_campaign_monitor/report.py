from __future__ import annotations

from collections import Counter
from pathlib import Path

from .deals import assess_deal
from .models import Change


def render_report(changes: list[Change], failures: dict[str, str]) -> str:
    counts = Counter(change.kind for change in changes)
    lines = [
        "# 航空公司官方促销变化",
        "",
        f"NEW: {counts['NEW']} / UPDATED: {counts['UPDATED']} / EXPIRED: {counts['EXPIRED']}",
        "",
    ]
    for kind in ("NEW", "UPDATED", "EXPIRED"):
        selected = [change for change in changes if change.kind == kind]
        selected.sort(key=lambda change: -assess_deal(change.campaign).score)
        if not selected:
            continue
        lines.extend([f"## {kind}", ""])
        for change in selected:
            campaign = change.campaign
            relevance = campaign.get("relevance", "general")
            deal = assess_deal(campaign)
            lines.append(
                f"- **[{campaign['airline']}] [{campaign['title']}]({campaign['url']})**"
                f"（关注度：{relevance}；优惠力度：{deal.strength}）"
            )
            if deal.highlights:
                lines.append(f"  - 优惠亮点：{'；'.join(deal.highlights)}")
            if campaign.get("booking_period"):
                lines.append(f"  - 购票期：{campaign['booking_period']}")
            if campaign.get("travel_period"):
                lines.append(f"  - 旅行期：{campaign['travel_period']}")
            if campaign.get("matched_origins"):
                lines.append(f"  - 出发地命中：{', '.join(campaign['matched_origins'])}")
            if campaign.get("matched_destinations"):
                lines.append(f"  - 目的地区域命中：{', '.join(campaign['matched_destinations'])}")
        lines.append("")
    if failures:
        lines.extend(["## 本次抓取失败（未影响其他航司）", ""])
        lines.extend(f"- {airline}: `{message[:300]}`" for airline, message in sorted(failures.items()))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_report(path: Path, changes: list[Change], failures: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(changes, failures), encoding="utf-8")
