from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import re


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


@dataclass(frozen=True)
class Campaign:
    airline: str
    title: str
    url: str
    summary: str = ""
    booking_period: str = ""
    travel_period: str = ""
    matched_origins: tuple[str, ...] = field(default_factory=tuple)
    matched_destinations: tuple[str, ...] = field(default_factory=tuple)
    relevance: str = "LOW"
    deal_strength: str = "NORMAL"
    has_explicit_price: bool = False
    has_promotion: bool = False
    core_route_change: bool = False
    notify: bool = False
    reason: str = ""
    relevance_score: int = 0

    @property
    def campaign_id(self) -> str:
        identity = f"{self.airline}|{self.url.rstrip('/').lower()}"
        return sha256(identity.encode("utf-8")).hexdigest()[:20]

    @property
    def content_hash(self) -> str:
        payload = {
            "title": compact_text(self.title),
            "summary": compact_text(self.summary),
            "booking_period": compact_text(self.booking_period),
            "travel_period": compact_text(self.travel_period),
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return sha256(encoded.encode("utf-8")).hexdigest()

    def to_record(self, today: str) -> dict:
        record = asdict(self)
        record["matched_origins"] = list(self.matched_origins)
        record["matched_destinations"] = list(self.matched_destinations)
        record["origin_match"] = list(self.matched_origins)
        record["destination_match"] = list(self.matched_destinations)
        record.update(
            {
                "id": self.campaign_id,
                "content_hash": self.content_hash,
                "active": True,
                "first_seen": today,
                "last_changed": today,
                "missing_runs": 0,
            }
        )
        return record


@dataclass(frozen=True)
class Change:
    kind: str
    campaign: dict
    previous: dict | None = None

