from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path

from .models import Campaign, Change
from .deals import record_is_expired

SCHEMA_VERSION = 1
EXPIRE_AFTER_MISSES = 2
SOURCE_FIELDS = ("title", "summary", "booking_period", "travel_period")


def _source_changed(old: dict, candidate: dict) -> bool:
    """Ignore scoring-only migrations when deciding whether content changed."""
    return any(str(old.get(key) or "").strip() != str(candidate.get(key) or "").strip() for key in SOURCE_FIELDS)


def empty_state() -> dict:
    return {"schema_version": SCHEMA_VERSION, "campaigns": {}}


def load_state(path: Path) -> tuple[dict, bool]:
    if not path.exists():
        return empty_state(), True
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != SCHEMA_VERSION or not isinstance(raw.get("campaigns"), dict):
        raise ValueError(f"不支持的状态文件格式: {path}")
    return raw, not bool(raw["campaigns"])


def reconcile(
    previous_state: dict,
    current: list[Campaign],
    successful_airlines: set[str],
    *,
    today: str | None = None,
) -> tuple[dict, list[Change]]:
    today = today or date.today().isoformat()
    state = deepcopy(previous_state)
    records: dict[str, dict] = state["campaigns"]
    changes: list[Change] = []
    seen_ids: set[str] = set()

    for campaign_id, old in list(records.items()):
        if record_is_expired(old, date.fromisoformat(today)):
            del records[campaign_id]
            changes.append(Change("EXPIRED", old.copy(), old.copy()))

    for campaign in current:
        fresh_record = campaign.to_record(today)
        if record_is_expired(fresh_record, date.fromisoformat(today)):
            continue
        campaign_id = campaign.campaign_id
        seen_ids.add(campaign_id)
        old = records.get(campaign_id)
        if old is None:
            new_record = campaign.to_record(today)
            records[campaign_id] = new_record
            changes.append(Change("NEW", new_record))
            continue

        candidate = campaign.to_record(old.get("first_seen", today))
        candidate["first_seen"] = old.get("first_seen", today)
        candidate["last_changed"] = old.get("last_changed", today)
        if _source_changed(old, candidate) or not old.get("active", True):
            candidate["last_changed"] = today
            changes.append(Change("UPDATED", candidate, old))
        records[campaign_id] = candidate

    for campaign_id, old in list(records.items()):
        if campaign_id in seen_ids or old.get("airline") not in successful_airlines or not old.get("active", True):
            continue
        missing_runs = int(old.get("missing_runs", 0)) + 1
        old["missing_runs"] = missing_runs
        if missing_runs >= EXPIRE_AFTER_MISSES:
            old["last_changed"] = today
            changes.append(Change("EXPIRED", old.copy(), old.copy()))
            del records[campaign_id]

    state["campaigns"] = dict(sorted(records.items()))
    return state, changes


def save_state_if_changed(path: Path, old_state: dict, new_state: dict) -> bool:
    if old_state == new_state:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(new_state, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(payload, encoding="utf-8")
    return True
