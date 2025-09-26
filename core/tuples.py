# core/tuples.py
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict


@dataclass
class TimeWindow:
    start: Optional[datetime]  # ISO datetime (can be timezone-aware)
    end: Optional[datetime]

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Optional[str]]):
        def _parse(s):
            if s is None: return None
            return datetime.fromisoformat(s)
        return cls(start=_parse(d.get("start")), end=_parse(d.get("end")))


@dataclass
class TemporalContext:
    timestamp: datetime
    timezone: str
    business_hours: bool
    emergency_override: bool
    access_window: Optional[TimeWindow]
    data_freshness_seconds: Optional[int]
    situation: Optional[str]
    temporal_role: Optional[str]
    event_correlation: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "timezone": self.timezone,
            "business_hours": self.business_hours,
            "emergency_override": self.emergency_override,
            "access_window": self.access_window.to_dict() if self.access_window else None,
            "data_freshness_seconds": self.data_freshness_seconds,
            "situation": self.situation,
            "temporal_role": self.temporal_role,
            "event_correlation": self.event_correlation,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        ts = datetime.fromisoformat(d["timestamp"])
        aw = None
        if d.get("access_window"):
            aw = TimeWindow.from_dict(d["access_window"])
        return cls(
            timestamp=ts,
            timezone=d.get("timezone", "UTC"),
            business_hours=bool(d.get("business_hours", False)),
            emergency_override=bool(d.get("emergency_override", False)),
            access_window=aw,
            data_freshness_seconds=d.get("data_freshness_seconds"),
            situation=d.get("situation"),
            temporal_role=d.get("temporal_role"),
            event_correlation=d.get("event_correlation"),
        )


@dataclass
class EnhancedContextualIntegrityTuple:
    data_type: str
    data_subject: str
    data_sender: str
    data_recipient: str
    transmission_principle: str
    temporal_context: TemporalContext

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_type": self.data_type,
            "data_subject": self.data_subject,
            "data_sender": self.data_sender,
            "data_recipient": self.data_recipient,
            "transmission_principle": self.transmission_principle,
            "temporal_context": self.temporal_context.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        return cls(
            data_type=d["data_type"],
            data_subject=d["data_subject"],
            data_sender=d["data_sender"],
            data_recipient=d["data_recipient"],
            transmission_principle=d.get("transmission_principle", ""),
            temporal_context=TemporalContext.from_dict(d["temporal_context"]),
        )
