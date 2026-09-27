"""Expand recurring weekly TimeWindows into concrete datetime intervals."""
from datetime import date, datetime, time, timedelta, tzinfo
from typing import List, Optional, Tuple

from app.schemas.sign import ParkingRule, TimeWindow, Weekday

Interval = Tuple[datetime, datetime]  # half-open: [start, end)

# Indexed by date.weekday() (Monday == 0).
_WEEKDAYS = (
    Weekday.MON,
    Weekday.TUE,
    Weekday.WED,
    Weekday.THU,
    Weekday.FRI,
    Weekday.SAT,
    Weekday.SUN,
)


def weekday_of(d: date) -> Weekday:
    return _WEEKDAYS[d.weekday()]


def _window_intervals(window: TimeWindow, first_day: date, last_day: date, tz: tzinfo) -> List[Interval]:
    start_t = window.start or time(0, 0)
    end_t = window.end or time(0, 0)
    crosses_midnight = window.end is None or end_t <= start_t

    result = []
    day = first_day
    while day <= last_day:
        if not window.days or weekday_of(day) in window.days:
            start = datetime.combine(day, start_t, tzinfo=tz)
            end_day = day + timedelta(days=1) if crosses_midnight else day
            result.append((start, datetime.combine(end_day, end_t, tzinfo=tz)))
        day += timedelta(days=1)
    return result


def rule_intervals(rule: ParkingRule, horizon_start: datetime, horizon_end: datetime) -> List[Interval]:
    """All intervals in which `rule` is in force, overlapping [horizon_start, horizon_end).

    A rule without windows is in force for the whole horizon.
    """
    if not rule.windows:
        return [(horizon_start, horizon_end)]

    tz = horizon_start.tzinfo
    # Start one day early so windows that began yesterday and cross midnight are included.
    first_day = horizon_start.date() - timedelta(days=1)
    last_day = horizon_end.date()
    intervals = []
    for window in rule.windows:
        intervals.extend(_window_intervals(window, first_day, last_day, tz))
    relevant = sorted(i for i in intervals if i[0] < horizon_end and i[1] > horizon_start)
    return _merge(relevant)


def _merge(intervals: List[Interval]) -> List[Interval]:
    """Merge overlapping or touching intervals (input must be sorted)."""
    merged: List[Interval] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def interval_containing(intervals: List[Interval], t: datetime) -> Optional[Interval]:
    for start, end in intervals:
        if start <= t < end:
            return (start, end)
    return None
