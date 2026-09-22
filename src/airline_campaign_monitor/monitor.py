from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .adapters import ALL_ADAPTERS
from .csv_export import save_csv_if_changed
from .http import HttpClient
from .report import write_report
from .state import load_state, reconcile, save_state_if_changed


def run(
    state_path: Path,
    report_path: Path,
    csv_path: Path | None = None,
    best_deals_path: Path | None = None,
) -> int:
    csv_path = csv_path or state_path.parent / "csv" / "my_campaigns.csv"
    best_deals_path = best_deals_path or state_path.parent / "csv" / "my_best_deals.csv"
    old_state, is_baseline = load_state(state_path)
    client = HttpClient()
    campaigns = []
    failures: dict[str, str] = {}
    successful_airlines: set[str] = set()

    for adapter_class in ALL_ADAPTERS:
        adapter = adapter_class(client)
        try:
            found = adapter.fetch()
            campaigns.extend(found)
            successful_airlines.add(adapter.airline)
            print(f"[OK] {adapter.airline}: {len(found)} campaigns")
        except Exception as exc:
            failures[adapter.airline] = str(exc)
            print(f"[WARN] {adapter.airline}: {exc}", file=sys.stderr)

    if not successful_airlines:
        print("[ERROR] 所有航空公司均抓取失败；保留原状态。", file=sys.stderr)
        return 2

    new_state, changes = reconcile(old_state, campaigns, successful_airlines)
    state_changed = save_state_if_changed(state_path, old_state, new_state)
    csv_changed = save_csv_if_changed(csv_path, new_state)
    best_deals_changed = save_csv_if_changed(best_deals_path, new_state, best_only=True)
    report_path.unlink(missing_ok=True)

    notification_changes = [change for change in changes if change.campaign.get("notify", False)]

    if is_baseline:
        print(f"[BASELINE] 已保存 {len(campaigns)} 条现有活动，不发送通知。")
    elif notification_changes:
        write_report(report_path, notification_changes)
        print(
            f"[CHANGE] 共 {len(changes)} 条状态变化，其中 {len(notification_changes)} 条满足通知规则；"
            f"报告已写入 {report_path}"
        )
    elif changes:
        print(f"[CHANGE] {len(changes)} 条状态变化均为低相关内容，仅记录，不发送通知。")
    else:
        print("[NO CHANGE] 未发现促销变化。")

    print(f"[STATE] {'changed' if state_changed else 'unchanged'}")
    print(f"[CSV] {'changed' if csv_changed else 'unchanged'}: {csv_path}")
    print(f"[BEST DEALS] {'changed' if best_deals_changed else 'unchanged'}: {best_deals_path}")
    if failures:
        print(f"[PARTIAL] {len(failures)} 家失败，其余结果已处理。", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor official airline campaigns")
    parser.add_argument("--state", type=Path, default=Path("data/campaigns.json"))
    parser.add_argument("--csv", type=Path, default=Path("data/csv/my_campaigns.csv"))
    parser.add_argument("--best-deals", type=Path, default=Path("data/csv/my_best_deals.csv"))
    parser.add_argument("--report", type=Path, default=Path("runtime/change.md"))
    args = parser.parse_args()
    return run(args.state, args.report, args.csv, args.best_deals)


if __name__ == "__main__":
    raise SystemExit(main())
