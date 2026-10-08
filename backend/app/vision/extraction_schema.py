"""The schema the Vision model fills, and its deterministic conversion to ParkingSignData.

Kept separate from `app.schemas.sign` on purpose: this one is shaped for a
language model (plain strings, descriptions as instructions, an explicit place
to report what it could not express), while `ParkingSignData` is shaped for the
rule engine. `to_sign_data` is the only bridge between them.
"""
from typing import List, Optional

from pydantic import BaseModel, Field, ValidationError

from app.schemas.sign import (
    CurbMarking,
    ParkingRule,
    ParkingSignData,
    ResidentZone,
    RuleType,
    TimeWindow,
    Weekday,
)

_HHMM = r"^([01][0-9]|2[0-3]):[0-5][0-9]$"


class ExtractedWindow(BaseModel):
    days: List[Weekday] = Field(
        description="Days the window applies. Empty list = every day. "
        "Hebrew: א=sun ב=mon ג=tue ד=wed ה=thu ו=fri ש/שבת=sat; 'א-ה' = sun..thu."
    )
    start: Optional[str] = Field(
        description="Start time HH:MM (24h), exactly as printed. null only if the rule applies all day.",
        pattern=_HHMM,
    )
    end: Optional[str] = Field(
        description="End time HH:MM (24h). Write 24:00 as 00:00. null only if the rule applies all day.",
        pattern=_HHMM,
    )


class ExtractedRule(BaseModel):
    rule_type: RuleType = Field(
        description="no_stopping: red X on blue (אין עצירה). no_parking: single red slash on blue (אין חניה). "
        "paid: parking requires payment (חניה בתשלום / הסדר חניה). time_limited: free but limited duration. "
        "residents_only: only permit holders of listed zones (לבעלי תו אזור ... בלבד). "
        "loading_zone: loading/unloading only (פריקה וטעינה). disabled_only: disabled permit holders only (נכים)."
    )
    windows: List[ExtractedWindow] = Field(
        description="When this rule applies. Empty list ONLY if the sign states it applies at all times."
    )
    max_duration_minutes: Optional[int] = Field(description="Maximum stay in minutes if printed, else null.")
    price_per_hour: Optional[float] = Field(description="Price in ILS per hour if printed, else null.")
    exempt_resident_zones: List[str] = Field(
        description="Resident zone identifiers exempt from this rule, as printed (e.g. '2'). "
        "For residents_only: the zones that may park."
    )
    exempt_local_zone: bool = Field(
        description="true if the sign refers to residents of the local zone WITHOUT printing a zone "
        "number (e.g. 'לתושבי האזור'). Never true when a zone number is printed."
    )
    exempt_disabled: Optional[bool] = Field(
        description="true if the sign explicitly exempts disabled permit holders, false if it explicitly "
        "includes them, null if the sign does not say."
    )
    raw_text: str = Field(description="The Hebrew text of this rule, transcribed exactly.")


class SignExtraction(BaseModel):
    sign_detected: bool = Field(description="Whether a parking-related sign is visible in the photo.")
    is_legible: bool = Field(description="Whether every part of the sign can be read with certainty.")
    confidence: float = Field(ge=0, le=1, description="Confidence that every extracted value is correct.")
    curb_marking: CurbMarking = Field(
        description="Curb paint nearest the camera: blue_white, red_white, gray (unpainted), none (no curb "
        "visible), unknown (visible but color unclear)."
    )
    rules: List[ExtractedRule]
    unreadable_fields: List[str] = Field(
        description="Parts of the sign that are blurred, cut off or occluded, e.g. 'hours', 'days', 'price', 'zone'."
    )
    free_outside_windows: bool = Field(
        description="true if the sign states parking is free at all other days and times, e.g. "
        "'ביתר הימים והשעות חינם', 'בשאר השעות החניה חופשית', 'ביתר הימים והשעות כולל שבת חינם'. "
        "This is supported: do NOT also list it in unsupported_conditions."
    )
    unsupported_conditions: List[str] = Field(
        description="Conditions on the sign that the rules above cannot express, e.g. holiday eves, events, "
        "vehicle weight or type limits other than commercial loading. Hebrew as printed."
    )


def to_sign_data(extraction: SignExtraction) -> ParkingSignData:
    """Convert model output to the rule engine's input. Raises ValidationError if inconsistent."""
    return ParkingSignData(
        sign_detected=extraction.sign_detected,
        is_legible=extraction.is_legible,
        confidence=extraction.confidence,
        curb_marking=extraction.curb_marking,
        unreadable_fields=extraction.unreadable_fields,
        # The engine returns UNKNOWN for these rather than a verdict that ignores them.
        unsupported_conditions=extraction.unsupported_conditions,
        free_outside_windows=extraction.free_outside_windows,
        rules=[
            ParkingRule(
                rule_type=rule.rule_type,
                windows=[TimeWindow(days=w.days, start=w.start, end=w.end) for w in rule.windows],
                max_duration_minutes=rule.max_duration_minutes,
                price_per_hour=rule.price_per_hour,
                # City is deliberately left unset: it is resolved from GPS, so the
                # model's spelling of a city name never affects permit matching.
                exempt_resident_zones=[ResidentZone(zone=z) for z in rule.exempt_resident_zones],
                exempt_local_zone=rule.exempt_local_zone,
                exempt_disabled=rule.exempt_disabled,
                raw_text=rule.raw_text,
            )
            for rule in extraction.rules
        ],
    )


def unreadable_result() -> ParkingSignData:
    """Engine input for model output we cannot trust: always yields UNKNOWN, never a guess."""
    return ParkingSignData(sign_detected=True, is_legible=False, confidence=0.0)


__all__ = ["SignExtraction", "ValidationError", "to_sign_data", "unreadable_result"]
