import csv
from datetime import date
from io import StringIO
from pathlib import Path
import importlib.util
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('focus_views',ROOT/'scripts/update_focus.py')
focus=importlib.util.module_from_spec(spec)
spec.loader.exec_module(focus)
TODAY=date(2026,10,25)


def test_build_is_repeatable_and_does_not_write_source_files():
    files=[p for p in ROOT.rglob('*') if p.is_file() and p.suffix in {'.csv','.json','.yaml'}]
    before={p:p.read_bytes() for p in files}
    first=focus.build(ROOT,TODAY)
    assert first == focus.build(ROOT,TODAY)
    assert first
    assert all(data.startswith(b'\xef\xbb\xbf') for data in first.values())
    assert before == {p:p.read_bytes() for p in files}


def test_deadlines_newness_and_origin_priority_are_source_based():
    records={
        'core':{'origin_match':['HGH'],'booking_period':'2026-10-20 至 2026-10-27','first_seen':'2026-10-25'},
        'unknown':{'booking_period':'','travel_period':'2027-01-01 至 2027-02-01','summary':'历史活动 2024-11-01','first_seen':'2026-09-01'},
        'expired':{'booking_period':'2026-10-01 至 2026-10-24'},
    }
    rows=[{'官方链接':url} for url in ('unknown','expired','core')]
    output=focus.mark_rows(rows,records,TODAY)
    assert len(output)==2 and output[0]['官方链接']=='core'
    assert all(word in output[0]['重点标记'] for word in ('匹配关注出发地','7天内截止','近7天新增'))
    assert output[1]['购票截止日期']=='' and '需人工核实' in output[1]['截止日期说明']
    assert focus.booking_deadline({'booking_period':'10月27日'}) is None
    assert focus.mark_rows([{'官方链接':'core'}],records,date(2026,11,1))==[]
