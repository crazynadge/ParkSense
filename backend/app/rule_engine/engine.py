"""Deterministic parking rule engine.

Pure function of (sign data, time, user profile, resolved location): same input -> same output.
No I/O, no AI calls, no randomness.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

from app.rule_engine.intervals import Interval, interval_containing, rule_intervals
from app.rule_engine.policy import (
    DEFAULT_TIMEZONE,
    DISABLED_DEFAULT_EXEMPT_RULES,
    LOOKAHEAD_DAYS,
    MIN_EXTRACTION_CONFIDENCE,
)
from app.schemas.decision import (
    CostInfo,
    CostType,
    ParkingDecision,
    ParkingStatus,
    PermittedBy,
    Reason,
    ReasonCode,
    UpcomingChange,
)
from app.schemas.location import LocationContext
from app.schemas.profile import UserProfile, VehicleType
from app.schemas.sign import CurbMarking, ParkingRule, ParkingSignData, RuleType

# A rule that forbids parking for everyone outranks one we cannot determine for this user.
_SEVERITY = {ParkingStatus.GREEN: 0, ParkingStatus.ORANGE: 1, ParkingStatus.UNKNOWN: 2, ParkingStatus.RED: 3}
_NOT_ALLOWED = (ParkingStatus.RED, ParkingStatus.UNKNOWN)

_SUMMARIES = {
    ParkingStatus.GREEN: "Parking allowed",
    ParkingStatus.ORANGE: "Parking allowed with conditions",
    ParkingStatus.RED: "Parking not allowed",
    ParkingStatus.UNKNOWN: "Could not determine - check the sign yourself",
}


@dataclass(frozen=True)
class _RuleOutcome:
    status: ParkingStatus
    cost: CostInfo
    reason: Reason
    max_duration_minutes: Optional[int] = None


@dataclass
class _Snapshot:
    """The combined verdict for a single moment in time."""

    status: ParkingStatus
    cost: CostInfo
    reasons: List[Reason]
    duration_deadline: Optional[datetime] = None  # leave-by time imposed by a max-duration rule
    warnings: List[Reason] = field(default_factory=list)


@dataclass(frozen=True)
class _Exemption:
    permitted_by: PermittedBy
    params: Dict[str, str]


@dataclass(frozen=True)
class _Undetermined:
    """Whether the user's permit applies cannot be established from the location we have."""

    reason: Reason


_FREE = CostInfo(type=CostType.FREE)
_EXEMPT = CostInfo(type=CostType.EXEMPT)


def _reason(
    code: ReasonCode,
    message: str,
    permitted_by: Optional[PermittedBy] = None,
    params: Optional[Dict[str, str]] = None,
) -> Reason:
    return Reason(code=code, message=message, permitted_by=permitted_by, params=params or {})


def evaluate(
    sign: ParkingSignData,
    now: datetime,
    profile: UserProfile,
    location: Optional[LocationContext] = None,
) -> ParkingDecision:
    """Decide whether `profile` may park at the scanned spot at `now`.

    `now` without tzinfo is interpreted in Israel local time. `location` (the resolved GPS
    fix) supplies the city and zone for resident permits and cross-checks the zone read
    from the sign.
    """
    now = now.replace(tzinfo=DEFAULT_TIMEZONE) if now.tzinfo is None else now.astimezone(DEFAULT_TIMEZONE)

    if sign.curb_marking == CurbMarking.RED_WHITE:
        # Decisive on its own and the conservative answer, even if the sign is unreadable.
        reason = _reason(ReasonCode.RED_WHITE_CURB, "Red-white curb: no stopping at any time")
        return _decision(now, _Snapshot(ParkingStatus.RED, _FREE, [reason]), location=location)

    unknown_reason = _insufficient_input(sign)
    if unknown_reason:
        snapshot = _Snapshot(ParkingStatus.UNKNOWN, CostInfo(type=CostType.UNKNOWN), [unknown_reason])
        return _decision(now, snapshot, location=location)

    horizon_end = now + timedelta(days=LOOKAHEAD_DAYS)
    schedule = [(rule, rule_intervals(rule, now, horizon_end)) for rule in sign.rules]

    free_reason = (
        _reason(ReasonCode.FREE_OUTSIDE_HOURS, "The sign states parking is free outside its listed hours")
        if sign.free_outside_windows
        else _reason(ReasonCode.NO_RESTRICTION, "No restriction in force")
    )
    current = _snapshot_at(now, schedule, profile, location, free_reason)
    boundaries = sorted({b for _, ivs in schedule for iv in ivs for b in iv if now < b < horizon_end})

    allowed_until: Optional[datetime] = None
    next_change: Optional[UpcomingChange] = None
    for boundary in boundaries:
        later = _snapshot_at(boundary, schedule, profile, location, free_reason)
        if next_change is None and (later.status, later.cost) != (current.status, current.cost):
            next_change = UpcomingChange(at=boundary, status=later.status, reasons=later.reasons)
        if current.status in _NOT_ALLOWED:
            if next_change is not None:
                break
        elif later.status in _NOT_ALLOWED:
            allowed_until = boundary
            break

    if current.duration_deadline and (allowed_until is None or current.duration_deadline < allowed_until):
        allowed_until = current.duration_deadline

    return _decision(now, current, allowed_until, next_change, location)


def _insufficient_input(sign: ParkingSignData) -> Optional[Reason]:
    """Fallback mechanism: a reason to refuse a verdict, or None if the input is usable."""
    if sign.sign_detected and not sign.is_legible:
        return _reason(ReasonCode.SIGN_ILLEGIBLE, "The sign is not legible")
    if sign.sign_detected and sign.confidence < MIN_EXTRACTION_CONFIDENCE:
        return _reason(ReasonCode.LOW_CONFIDENCE, "Low confidence reading the sign")
    if sign.unreadable_fields:
        fields = ",".join(sign.unreadable_fields)
        return _reason(ReasonCode.PARTIAL_SIGN, "Parts of the sign could not be read", params={"fields": fields})
    if sign.unsupported_conditions:
        return _reason(
            ReasonCode.UNSUPPORTED_CONDITION,
            "The sign has conditions the engine cannot evaluate",
            params={"conditions": " | ".join(sign.unsupported_conditions)},
        )
    if not sign.sign_detected and sign.curb_marking == CurbMarking.UNKNOWN:
        return _reason(ReasonCode.NOTHING_DETECTED, "No sign or curb marking detected")
    if sign.curb_marking == CurbMarking.BLUE_WHITE and not sign.rules:
        return _reason(ReasonCode.PAID_HOURS_UNKNOWN, "Blue-white curb, but paid-parking hours are unknown")
    return None


def _snapshot_at(
    t: datetime,
    schedule: List[Tuple[ParkingRule, List[Interval]]],
    profile: UserProfile,
    location: Optional[LocationContext],
    free_reason: Reason,
) -> _Snapshot:
    active: List[Tuple[_RuleOutcome, Interval]] = []
    warnings: List[Reason] = []
    for rule, intervals in schedule:
        interval = interval_containing(intervals, t)
        if interval is not None:
            outcome, rule_warnings = _rule_outcome(rule, profile, location)
            active.append((outcome, interval))
            warnings.extend(rule_warnings)

    if not active:
        return _Snapshot(ParkingStatus.GREEN, _FREE, [free_reason])

    status = max((o.status for o, _ in active), key=_SEVERITY.__getitem__)
    reasons = [o.reason for o, _ in active]
    cost = CostInfo(type=CostType.UNKNOWN) if status == ParkingStatus.UNKNOWN else _combine_costs([o.cost for o, _ in active])
    snapshot = _Snapshot(status, cost, reasons, warnings=warnings)

    for outcome, (_, interval_end) in active:
        if outcome.max_duration_minutes is None:
            continue
        deadline = t + timedelta(minutes=outcome.max_duration_minutes)
        # Only a deadline that falls while the rule is still in force actually binds.
        if deadline < interval_end and (snapshot.duration_deadline is None or deadline < snapshot.duration_deadline):
            snapshot.duration_deadline = deadline
    return snapshot


def _rule_outcome(
    rule: ParkingRule, profile: UserProfile, location: Optional[LocationContext]
) -> Tuple[_RuleOutcome, List[Reason]]:
    """What a single in-force rule means for this particular user."""
    warnings: List[Reason] = []
    rt = rule.rule_type
    red = ParkingStatus.RED

    if rt == RuleType.NO_STOPPING:
        return _RuleOutcome(red, _FREE, _reason(ReasonCode.NO_STOPPING, "No stopping")), warnings
    if rt == RuleType.NO_PARKING:
        return _RuleOutcome(red, _FREE, _reason(ReasonCode.NO_PARKING, "No parking")), warnings
    if rt == RuleType.DISABLED_ONLY:
        if profile.has_disabled_permit:
            reason = _reason(ReasonCode.DISABLED_ONLY, "Disabled parking", PermittedBy.DISABLED_PERMIT)
            return _RuleOutcome(ParkingStatus.GREEN, _FREE, reason), warnings
        return _RuleOutcome(red, _FREE, _reason(ReasonCode.DISABLED_ONLY, "Disabled parking")), warnings
    if rt == RuleType.LOADING_ZONE:
        if profile.vehicle_type == VehicleType.COMMERCIAL:
            reason = _reason(ReasonCode.LOADING_ZONE, "Loading zone", PermittedBy.COMMERCIAL_VEHICLE)
            return _RuleOutcome(ParkingStatus.ORANGE, _FREE, reason, rule.max_duration_minutes), warnings
        return _RuleOutcome(red, _FREE, _reason(ReasonCode.LOADING_ZONE, "Loading zone")), warnings

    exemption = _exemption(rule, profile, location)
    undetermined = exemption.reason if isinstance(exemption, _Undetermined) else None

    def exempt(code: ReasonCode, message: str) -> _RuleOutcome:
        assert isinstance(exemption, _Exemption)
        reason = _reason(code, message, exemption.permitted_by, exemption.params)
        return _RuleOutcome(ParkingStatus.GREEN, _EXEMPT, reason)

    if rt == RuleType.RESIDENTS_ONLY:
        if isinstance(exemption, _Exemption):
            return exempt(ReasonCode.RESIDENTS_ONLY, "Residents-only parking"), warnings
        if undetermined:
            # Neither verdict is safe: "forbidden" may be wrong for a resident, "allowed" may get them towed.
            return _RuleOutcome(ParkingStatus.UNKNOWN, CostInfo(type=CostType.UNKNOWN), undetermined), warnings
        return _RuleOutcome(red, _FREE, _reason(ReasonCode.RESIDENTS_ONLY, "Residents-only parking")), warnings
    # For paid and time-limited rules, the non-exempt verdict is always safe (paying or
    # leaving on time is legal for everyone), so an unverifiable permit only adds a warning.
    if undetermined:
        warnings.append(undetermined)
    if rt == RuleType.PAID:
        if isinstance(exemption, _Exemption):
            return exempt(ReasonCode.PAID, "Paid parking"), warnings
        if rule.price_per_hour is None:
            warnings.append(_reason(ReasonCode.PAID_RATE_UNKNOWN, "Hourly rate not printed or not read"))
        cost = CostInfo(type=CostType.PAID, price_per_hour=rule.price_per_hour)
        reason = _reason(ReasonCode.PAID, "Paid parking")
        return _RuleOutcome(ParkingStatus.ORANGE, cost, reason, rule.max_duration_minutes), warnings
    if rt == RuleType.TIME_LIMITED:
        if isinstance(exemption, _Exemption):
            return exempt(ReasonCode.TIME_LIMITED, "Time-limited parking"), warnings
        if rule.max_duration_minutes is None:
            warnings.append(_reason(ReasonCode.MAX_DURATION_UNKNOWN, "Maximum duration not read"))
        reason = _reason(ReasonCode.TIME_LIMITED, "Time-limited parking")
        return _RuleOutcome(ParkingStatus.ORANGE, _FREE, reason, rule.max_duration_minutes), warnings

    raise ValueError("Unhandled rule type: %s" % rt)  # pragma: no cover - enum is exhaustive


def _exemption(
    rule: ParkingRule, profile: UserProfile, location: Optional[LocationContext]
) -> Union[_Exemption, _Undetermined, None]:
    """Is the user exempt from `rule`? Cross-references resident permits with the GPS location.

    Returns an exemption, None (not exempt), or _Undetermined when the answer depends on
    a location we do not know precisely enough, or when the location contradicts the sign.
    """
    if profile.has_disabled_permit:
        exempt = rule.exempt_disabled
        if exempt is None:
            exempt = rule.rule_type in DISABLED_DEFAULT_EXEMPT_RULES
        if exempt:
            return _Exemption(PermittedBy.DISABLED_PERMIT, {})

    if not profile.resident_permits or not (rule.exempt_resident_zones or rule.exempt_local_zone):
        return None  # no permit can apply: nothing depends on the location

    gps_city = location.city if location and location.city_certain else None
    gps_zone = location.zone if location and location.zone_certain else None
    printed_zones = {_norm(z.zone) for z in rule.exempt_resident_zones}

    # (city printed on the sign or None, zone, whether the zone comes from GPS)
    candidates = [(z.city, z.zone, False) for z in rule.exempt_resident_zones]
    local_zone_unresolved = rule.exempt_local_zone and gps_zone is None
    if rule.exempt_local_zone and gps_zone is not None:
        candidates.append((None, gps_zone, True))

    undetermined: Optional[Reason] = None
    for permit in profile.resident_permits:
        for sign_city, zone, from_gps in candidates:
            if _norm(permit.zone) != _norm(zone):
                continue
            city = sign_city or gps_city
            if city is None:
                undetermined = undetermined or _reason(
                    ReasonCode.LOCATION_UNCERTAIN,
                    "Cannot verify which city this sign is in",
                    params={"zone": zone},
                )
                continue
            if _norm(city) != _norm(permit.city):
                continue
            # Cross-check: the zone printed on the sign should be the zone we are standing in.
            # A contradiction suggests a misread, so the permit is not trusted blindly.
            if (
                not from_gps
                and gps_zone is not None
                and location is not None
                and _norm(location.city or "") == _norm(city)
                and _norm(gps_zone) not in printed_zones
            ):
                undetermined = _reason(
                    ReasonCode.ZONE_MISMATCH,
                    "Zone read from the sign differs from the GPS zone",
                    params={"sign_zone": zone, "gps_zone": gps_zone},
                )
                continue
            return _Exemption(PermittedBy.RESIDENT_PERMIT, {"city": permit.city, "zone": permit.zone})

        if local_zone_unresolved and (gps_city is None or _norm(gps_city) == _norm(permit.city)):
            undetermined = undetermined or _reason(
                ReasonCode.LOCAL_ZONE_UNKNOWN, "Sign refers to local residents but the zone is not known"
            )

    return _Undetermined(undetermined) if undetermined else None


def _combine_costs(costs: List[CostInfo]) -> CostInfo:
    paid = [c for c in costs if c.type == CostType.PAID]
    if paid:
        prices = [c.price_per_hour for c in paid]
        return CostInfo(type=CostType.PAID, price_per_hour=None if None in prices else max(prices))
    if any(c.type == CostType.EXEMPT for c in costs):
        return _EXEMPT
    return _FREE


def _decision(
    now: datetime,
    snapshot: _Snapshot,
    allowed_until: Optional[datetime] = None,
    next_change: Optional[UpcomingChange] = None,
    location: Optional[LocationContext] = None,
) -> ParkingDecision:
    if snapshot.status in _NOT_ALLOWED:
        allowed_until = None
    max_stay = None if allowed_until is None else int((allowed_until - now).total_seconds() // 60)
    return ParkingDecision(
        status=snapshot.status,
        summary=_SUMMARIES[snapshot.status],
        evaluated_at=now,
        allowed_until=allowed_until,
        max_stay_minutes=max_stay,
        cost=snapshot.cost,
        next_change=next_change,
        reasons=snapshot.reasons,
        warnings=_dedupe(snapshot.warnings),
        location=location,
    )


def _dedupe(reasons: List[Reason]) -> List[Reason]:
    seen = set()
    unique = []
    for r in reasons:
        key = (r.code, tuple(sorted(r.params.items())))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def _norm(value: str) -> str:
    return value.strip().casefold()
