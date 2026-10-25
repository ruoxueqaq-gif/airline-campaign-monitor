from __future__ import annotations

import sys as _layout_sys
from pathlib import Path as _LayoutPath
_layout_sys.path.insert(0, str(_LayoutPath(__file__).resolve().parents[1]))
_layout_sys.path.insert(0, str(_LayoutPath(__file__).resolve().parents[1] / "src"))
from airline_campaign_monitor.layout import project_path

from datetime import date, timedelta
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from focus_common import day, number, read_table, table, run


import json
import re
from airline_campaign_monitor.deals import extract_dates, _labelled_dates, record_is_expired


def booking_deadline(record):
    # Only the purchase clause; a travel date or old news footnote is not a deadline.
    clause = re.split(r'旅行|出行|搭乘|搭乗|travel\s+(?:period|date)', str(record.get('booking_period') or ''), maxsplit=1, flags=re.I)[0]
    dates = extract_dates(clause) or _labelled_dates(str(record.get('summary') or ''), booking=True)
    return max(dates) if dates else None


def mark_rows(rows, records, today):
    output = []
    for row in rows:
        record = records.get(row.get('官方链接'), {})
        if record and record_is_expired(record, today):
            continue
        row = dict(row)
        origins = set(record.get('origin_match') or record.get('matched_origins') or [])
        origin_rank = 0 if origins & {'HGH','PVG','SHA'} else 1 if origins & {'NKG','NGB'} else 2
        deadline = booking_deadline(record)
        first = day(record.get('first_seen'))
        labels = []
        if origin_rank < 2:
            labels.append('⭐ 匹配关注出发地')
        if deadline and 0 <= (deadline - today).days <= 7:
            labels.append('🟠 7天内截止')
        if first and 0 <= (today - first).days <= 6:
            labels.append('🆕 近7天新增')
        row.update({'重点标记':'；'.join(labels), '购票截止日期':deadline.isoformat() if deadline else '',
                    '截止日期说明':'' if deadline else '官网未明确，需人工核实'})
        output.append((origin_rank, 0 if deadline and 0 <= (deadline-today).days <= 7 else 1, row))
    return [row for _, _, row in sorted(output, key=lambda item:(item[0], item[1]))]


def build(root, today):
    headers, rows = read_table(project_path(root, 'csv/01_重点关注/my_best_deals.csv'))
    state = json.loads((root / 'data/campaigns.json').read_text(encoding='utf-8'))
    records = {r.get('url'):r for r in state.get('campaigns', {}).values()}
    return {'csv/01_重点关注/01_my_best_deals.csv':table(['重点标记','购票截止日期','截止日期说明']+headers, mark_rows(rows, records, today))}


if __name__ == '__main__':
    raise SystemExit(run(build, ROOT))
