"""Static policy constants for the rule engine.

Anything here that encodes legal interpretation must be verified against current
Israeli traffic regulations / municipal bylaws before production.
"""
from zoneinfo import ZoneInfo

from app.schemas.sign import RuleType

DEFAULT_TIMEZONE = ZoneInfo("Asia/Jerusalem")

# Below this extraction confidence the engine returns UNKNOWN instead of a verdict.
MIN_EXTRACTION_CONFIDENCE = 0.75

# How far ahead we look for the next rule boundary (allowed_until / next_change).
LOOKAHEAD_DAYS = 7

# Rule types a disabled-permit holder is exempt from when the sign is silent on it.
# TODO(legal): verify against Israeli disabled parking regulations per municipality.
DISABLED_DEFAULT_EXEMPT_RULES = frozenset(
    {RuleType.PAID, RuleType.TIME_LIMITED, RuleType.RESIDENTS_ONLY}
)
