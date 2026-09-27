"""Structured representation of a parking sign + curb, as produced by the Vision layer.

This is the contract between the AI extraction module and the deterministic rule
engine. The Vision model's only job is to fill this schema; it never decides
whether parking is allowed.
"""
from datetime import time
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class Weekday(str, Enum):
    SUN = "sun"
    MON = "mon"
    TUE = "tue"
    WED = "wed"
    THU = "thu"
    FRI = "fri"
    SAT = "sat"


class CurbMarking(str, Enum):
    BLUE_WHITE = "blue_white"  # paid / regulated parking
    RED_WHITE = "red_white"  # no stopping at any time
    GRAY = "gray"  # unmarked, generally free unless a sign says otherwise
    NONE = "none"  # no curb visible / no marking
    UNKNOWN = "unknown"  # curb visible but color could not be determined


class RuleType(str, Enum):
    NO_STOPPING = "no_stopping"  # e.g. sign 432
    NO_PARKING = "no_parking"  # e.g. sign 433
    PAID = "paid"  # parking requires payment (e.g. Pango / Cellopark)
    TIME_LIMITED = "time_limited"  # free but limited to max_duration_minutes
    RESIDENTS_ONLY = "residents_only"  # only permit holders of listed zones
    LOADING_ZONE = "loading_zone"  # commercial loading / unloading only
    DISABLED_ONLY = "disabled_only"  # disabled permit holders only


class ResidentZone(BaseModel):
    """A municipal residential parking zone, e.g. Tel Aviv zone 2."""

    city: Optional[str] = Field(
        None,
        description="Municipality. May be omitted on a sign; resolved from GPS location.",
    )
    zone: str = Field(..., min_length=1, description="Zone identifier as printed, e.g. '2'.")


class TimeWindow(BaseModel):
    """A recurring weekly window during which a rule is in force.

    - `days` empty  -> every day.
    - `start`/`end` both omitted -> the whole day.
    - `end` <= `start` -> the window crosses midnight into the next day.
    """

    days: List[Weekday] = Field(default_factory=list)
    start: Optional[time] = None
    end: Optional[time] = None

    @model_validator(mode="after")
    def _check_bounds(self) -> "TimeWindow":
        if (self.start is None) != (self.end is None):
            raise ValueError("start and end must both be set or both be omitted")
        if self.start is not None and self.start == self.end:
            raise ValueError("start and end must differ; omit both for an all-day window")
        return self


class ParkingRule(BaseModel):
    """A single restriction printed on a sign (one sign can carry several)."""

    rule_type: RuleType
    windows: List[TimeWindow] = Field(
        default_factory=list, description="When the rule applies. Empty = always."
    )
    max_duration_minutes: Optional[int] = Field(None, gt=0)
    price_per_hour: Optional[float] = Field(None, ge=0, description="ILS per hour, if printed.")
    exempt_resident_zones: List[ResidentZone] = Field(
        default_factory=list,
        description="Residents of these zones are exempt (for RESIDENTS_ONLY: the permitted zones).",
    )
    exempt_local_zone: bool = Field(
        False,
        description="The sign exempts residents of the local zone without printing its number "
        "(e.g. 'לתושבי האזור'). The zone is then taken from the GPS location.",
    )
    exempt_disabled: Optional[bool] = Field(
        None,
        description="Explicit disabled-permit exemption on the sign. None = apply default policy.",
    )
    raw_text: Optional[str] = Field(None, description="Original sign text, for audit/debugging.")


class ParkingSignData(BaseModel):
    """Full extraction result for one scan."""

    schema_version: str = "1.0"
    sign_detected: bool
    is_legible: bool = True
    confidence: float = Field(..., ge=0.0, le=1.0)
    curb_marking: CurbMarking = CurbMarking.UNKNOWN
    rules: List[ParkingRule] = Field(default_factory=list)
    unreadable_fields: List[str] = Field(
        default_factory=list,
        description="Parts of the sign the extractor could not read (partial / occluded sign).",
    )
    unsupported_conditions: List[str] = Field(
        default_factory=list,
        description="Conditions read from the sign that the rule schema cannot express (e.g. holiday eves).",
    )
