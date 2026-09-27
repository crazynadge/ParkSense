from datetime import datetime, timedelta, timezone

import pytest

from app.rule_engine import evaluate
from app.rule_engine.policy import DEFAULT_TIMEZONE
from app.schemas import (
    CostType,
    CurbMarking,
    ParkingRule,
    ParkingSignData,
    ParkingStatus,
    PermittedBy,
    ReasonCode,
    ResidentPermit,
    ResidentZone,
    RuleType,
    TimeWindow,
    UserProfile,
    VehicleType,
    Weekday,
)

SUN_THU = [Weekday.SUN, Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU]
_WEEK_START = datetime(2026, 9, 27, tzinfo=DEFAULT_TIMEZONE)  # a Sunday
_DAY_OFFSET = {d: i for i, d in enumerate(["sun", "mon", "tue", "wed", "thu", "fri", "sat"])}


def at(day: str, hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return _WEEK_START + timedelta(days=_DAY_OFFSET[day], hours=h, minutes=m)


def sign(*rules, curb=CurbMarking.BLUE_WHITE, **kwargs) -> ParkingSignData:
    return ParkingSignData(
        sign_detected=kwargs.pop("sign_detected", True),
        confidence=kwargs.pop("confidence", 0.95),
        curb_marking=curb,
        rules=list(rules),
        **kwargs,
    )


def tel_aviv_sign() -> ParkingSignData:
    """Paid Sun-Thu 08-19 / Fri 08-13 (zone 2 exempt), residents of zone 2 only Sun-Thu 19-07."""
    return sign(
        ParkingRule(
            rule_type=RuleType.PAID,
            windows=[
                TimeWindow(days=SUN_THU, start="08:00", end="19:00"),
                TimeWindow(days=[Weekday.FRI], start="08:00", end="13:00"),
            ],
            price_per_hour=6.3,
            exempt_resident_zones=[ResidentZone(zone="2")],
        ),
        ParkingRule(
            rule_type=RuleType.RESIDENTS_ONLY,
            windows=[TimeWindow(days=SUN_THU, start="19:00", end="07:00")],
            exempt_resident_zones=[ResidentZone(zone="2")],
        ),
    )


VISITOR = UserProfile()
RESIDENT = UserProfile(resident_permits=[ResidentPermit(city="Tel Aviv", zone="2")])
OTHER_ZONE_RESIDENT = UserProfile(resident_permits=[ResidentPermit(city="Tel Aviv", zone="5")])
DISABLED = UserProfile(has_disabled_permit=True)


class TestPaidAndResidentZones:
    def test_visitor_during_paid_hours_is_orange_until_residents_only(self):
        d = evaluate(tel_aviv_sign(), at("mon", "10:00"), VISITOR, city="Tel Aviv")
        assert d.status == ParkingStatus.ORANGE
        assert d.cost.type == CostType.PAID
        assert d.cost.price_per_hour == 6.3
        assert d.allowed_until == at("mon", "19:00")
        assert d.max_stay_minutes == 9 * 60
        assert d.next_change.at == at("mon", "19:00")
        assert d.next_change.status == ParkingStatus.RED
        assert [r.code for r in d.next_change.reasons] == [ReasonCode.RESIDENTS_ONLY]
        assert d.next_change.reasons[0].permitted_by is None

    def test_resident_is_exempt_all_day(self):
        d = evaluate(tel_aviv_sign(), at("mon", "10:00"), RESIDENT, city="Tel Aviv")
        assert d.status == ParkingStatus.GREEN
        assert d.cost.type == CostType.EXEMPT
        assert d.allowed_until is None
        [reason] = d.reasons
        assert reason.code == ReasonCode.PAID
        assert reason.permitted_by == PermittedBy.RESIDENT_PERMIT
        assert reason.params == {"city": "Tel Aviv", "zone": "2"}

    def test_resident_of_other_zone_is_not_exempt(self):
        d = evaluate(tel_aviv_sign(), at("mon", "21:00"), OTHER_ZONE_RESIDENT, city="Tel Aviv")
        assert d.status == ParkingStatus.RED

    def test_same_zone_in_another_city_does_not_match(self):
        d = evaluate(tel_aviv_sign(), at("mon", "21:00"), RESIDENT, city="Givatayim")
        assert d.status == ParkingStatus.RED

    def test_unknown_city_does_not_apply_exemption_and_warns(self):
        d = evaluate(tel_aviv_sign(), at("mon", "10:00"), RESIDENT, city=None)
        assert d.status == ParkingStatus.ORANGE
        assert [(w.code, w.params) for w in d.warnings] == [(ReasonCode.RESIDENT_CITY_UNKNOWN, {"zone": "2"})]

    def test_visitor_at_night_is_red_until_morning(self):
        d = evaluate(tel_aviv_sign(), at("mon", "23:00"), VISITOR, city="Tel Aviv")
        assert d.status == ParkingStatus.RED
        assert d.allowed_until is None
        # Residents-only ends 07:00, a free hour, then paid from 08:00.
        assert d.next_change.at == at("tue", "07:00")
        assert d.next_change.status == ParkingStatus.GREEN

    def test_overnight_window_started_previous_day_is_active_after_midnight(self):
        d = evaluate(tel_aviv_sign(), at("tue", "02:00"), VISITOR, city="Tel Aviv")
        assert d.status == ParkingStatus.RED

    def test_friday_afternoon_is_free_through_the_weekend(self):
        d = evaluate(tel_aviv_sign(), at("fri", "14:00"), VISITOR, city="Tel Aviv")
        assert d.status == ParkingStatus.GREEN
        assert d.cost.type == CostType.FREE
        # Sunday 08:00 becomes paid (orange), Sunday 19:00 becomes residents-only (red).
        assert d.next_change.at == at("sun", "08:00") + timedelta(days=7)
        assert d.allowed_until == at("sun", "19:00") + timedelta(days=7)

    def test_disabled_permit_exempt_from_paid_and_residents_only(self):
        for t in (at("mon", "10:00"), at("mon", "22:00")):
            d = evaluate(tel_aviv_sign(), t, DISABLED, city="Tel Aviv")
            assert d.status == ParkingStatus.GREEN
            assert d.cost.type == CostType.EXEMPT

    def test_explicit_no_disabled_exemption_on_sign_wins(self):
        s = sign(ParkingRule(rule_type=RuleType.PAID, price_per_hour=5, exempt_disabled=False))
        d = evaluate(s, at("mon", "10:00"), DISABLED)
        assert d.status == ParkingStatus.ORANGE


class TestWarnings:
    def test_paid_without_rate_warns_once(self):
        s = sign(ParkingRule(rule_type=RuleType.PAID), ParkingRule(rule_type=RuleType.PAID))
        d = evaluate(s, at("mon", "10:00"), VISITOR)
        assert d.cost.price_per_hour is None
        assert [w.code for w in d.warnings] == [ReasonCode.PAID_RATE_UNKNOWN]


class TestTimeLimits:
    def test_max_duration_sets_allowed_until(self):
        s = sign(
            ParkingRule(
                rule_type=RuleType.TIME_LIMITED,
                windows=[TimeWindow(start="08:00", end="18:00")],
                max_duration_minutes=120,
            ),
            curb=CurbMarking.GRAY,
        )
        d = evaluate(s, at("mon", "10:00"), VISITOR)
        assert d.status == ParkingStatus.ORANGE
        assert d.cost.type == CostType.FREE
        assert d.allowed_until == at("mon", "12:00")
        assert d.max_stay_minutes == 120

    def test_max_duration_does_not_bind_past_window_end(self):
        s = sign(
            ParkingRule(
                rule_type=RuleType.TIME_LIMITED,
                windows=[TimeWindow(start="08:00", end="18:00")],
                max_duration_minutes=120,
            ),
            curb=CurbMarking.GRAY,
        )
        d = evaluate(s, at("mon", "17:00"), VISITOR)
        assert d.allowed_until is None
        assert d.next_change.at == at("mon", "18:00")
        assert d.next_change.status == ParkingStatus.GREEN


class TestProhibitions:
    def test_red_white_curb_is_always_red(self):
        d = evaluate(sign(curb=CurbMarking.RED_WHITE), at("mon", "10:00"), DISABLED)
        assert d.status == ParkingStatus.RED
        assert [r.code for r in d.reasons] == [ReasonCode.RED_WHITE_CURB]

    def test_red_white_curb_is_red_even_if_sign_illegible(self):
        s = sign(curb=CurbMarking.RED_WHITE, is_legible=False, confidence=0.2)
        assert evaluate(s, at("mon", "10:00"), VISITOR).status == ParkingStatus.RED

    def test_no_parking_during_window(self):
        s = sign(
            ParkingRule(rule_type=RuleType.NO_PARKING, windows=[TimeWindow(days=SUN_THU, start="07:00", end="09:00")]),
            curb=CurbMarking.GRAY,
        )
        assert evaluate(s, at("mon", "08:00"), VISITOR).status == ParkingStatus.RED
        d = evaluate(s, at("mon", "06:00"), VISITOR)
        assert d.status == ParkingStatus.GREEN
        assert d.allowed_until == at("mon", "07:00")
        assert d.max_stay_minutes == 60

    @pytest.mark.parametrize(
        "vehicle,expected", [(VehicleType.COMMERCIAL, ParkingStatus.ORANGE), (VehicleType.PRIVATE, ParkingStatus.RED)]
    )
    def test_loading_zone(self, vehicle, expected):
        s = sign(ParkingRule(rule_type=RuleType.LOADING_ZONE, max_duration_minutes=30), curb=CurbMarking.GRAY)
        d = evaluate(s, at("mon", "10:00"), UserProfile(vehicle_type=vehicle))
        assert d.status == expected
        if expected == ParkingStatus.ORANGE:
            assert d.max_stay_minutes == 30

    def test_disabled_only(self):
        s = sign(ParkingRule(rule_type=RuleType.DISABLED_ONLY), curb=CurbMarking.GRAY)
        assert evaluate(s, at("mon", "10:00"), DISABLED).status == ParkingStatus.GREEN
        assert evaluate(s, at("mon", "10:00"), VISITOR).status == ParkingStatus.RED

    def test_most_restrictive_rule_wins(self):
        s = sign(
            ParkingRule(rule_type=RuleType.PAID, price_per_hour=5),
            ParkingRule(rule_type=RuleType.NO_STOPPING, windows=[TimeWindow(start="16:00", end="19:00")]),
        )
        assert evaluate(s, at("mon", "17:00"), VISITOR).status == ParkingStatus.RED
        d = evaluate(s, at("mon", "15:00"), VISITOR)
        assert d.status == ParkingStatus.ORANGE
        assert d.allowed_until == at("mon", "16:00")


class TestFallback:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"is_legible": False},
            {"confidence": 0.5},
            {"unreadable_fields": ["hours"]},
        ],
    )
    def test_uncertain_extraction_returns_unknown(self, kwargs):
        d = evaluate(sign(ParkingRule(rule_type=RuleType.PAID), **kwargs), at("mon", "10:00"), VISITOR)
        assert d.status == ParkingStatus.UNKNOWN
        assert d.reasons[0].code in (ReasonCode.SIGN_ILLEGIBLE, ReasonCode.LOW_CONFIDENCE, ReasonCode.PARTIAL_SIGN)
        assert d.cost.type == CostType.UNKNOWN
        assert d.allowed_until is None

    def test_blue_white_curb_without_rules_is_unknown(self):
        d = evaluate(sign(sign_detected=False), at("mon", "10:00"), VISITOR)
        assert d.status == ParkingStatus.UNKNOWN

    def test_nothing_detected_is_unknown(self):
        d = evaluate(sign(curb=CurbMarking.UNKNOWN, sign_detected=False), at("mon", "10:00"), VISITOR)
        assert d.status == ParkingStatus.UNKNOWN

    def test_gray_curb_without_sign_is_free(self):
        d = evaluate(sign(curb=CurbMarking.GRAY, sign_detected=False), at("mon", "10:00"), VISITOR)
        assert d.status == ParkingStatus.GREEN
        assert d.cost.type == CostType.FREE


class TestDeterminism:
    def test_naive_time_is_treated_as_israel_local(self):
        naive = evaluate(tel_aviv_sign(), datetime(2026, 9, 28, 10, 0), VISITOR, city="Tel Aviv")
        aware = evaluate(tel_aviv_sign(), at("mon", "10:00"), VISITOR, city="Tel Aviv")
        assert naive == aware

    def test_utc_input_is_converted(self):
        utc = datetime(2026, 9, 28, 7, 0, tzinfo=timezone.utc)  # 10:00 in Israel (IDT, UTC+3)
        d = evaluate(tel_aviv_sign(), utc, VISITOR, city="Tel Aviv")
        assert d.evaluated_at == at("mon", "10:00")
        assert d.status == ParkingStatus.ORANGE
