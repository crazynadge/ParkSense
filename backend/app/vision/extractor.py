"""Vision extraction layer: image -> ParkingSignData.

Isolated from the rule engine on purpose. The only shared dependency is the
`ParkingSignData` schema. A Gemini Flash / GPT-4o-mini implementation will
implement `SignExtractor` in a later phase.
"""
from typing import Protocol

from app.schemas.sign import (
    CurbMarking,
    ParkingRule,
    ParkingSignData,
    ResidentZone,
    RuleType,
    TimeWindow,
    Weekday,
)


class SignExtractor(Protocol):
    async def extract(self, image: bytes) -> ParkingSignData:
        ...


class MockSignExtractor:
    """Returns a fixed, typical Tel Aviv blue-white sign regardless of the image."""

    async def extract(self, image: bytes) -> ParkingSignData:
        weekdays = [Weekday.SUN, Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU]
        return ParkingSignData(
            sign_detected=True,
            is_legible=True,
            confidence=0.95,
            curb_marking=CurbMarking.BLUE_WHITE,
            rules=[
                ParkingRule(
                    rule_type=RuleType.PAID,
                    windows=[
                        TimeWindow(days=weekdays, start="08:00", end="19:00"),
                        TimeWindow(days=[Weekday.FRI], start="08:00", end="13:00"),
                    ],
                    price_per_hour=6.3,
                    exempt_resident_zones=[ResidentZone(zone="2")],
                ),
                ParkingRule(
                    rule_type=RuleType.RESIDENTS_ONLY,
                    windows=[TimeWindow(days=weekdays, start="19:00", end="07:00")],
                    exempt_resident_zones=[ResidentZone(zone="2")],
                ),
            ],
        )
