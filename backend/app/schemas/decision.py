from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.location import LocationContext


class ReasonCode(str, Enum):
    """Stable, language-neutral codes. Clients localize these; never parse `message`."""

    # Verdict reasons
    NO_RESTRICTION = "no_restriction"
    FREE_OUTSIDE_HOURS = "free_outside_hours"  # the sign itself says free outside its hours
    RED_WHITE_CURB = "red_white_curb"
    NO_STOPPING = "no_stopping"
    NO_PARKING = "no_parking"
    DISABLED_ONLY = "disabled_only"
    LOADING_ZONE = "loading_zone"
    RESIDENTS_ONLY = "residents_only"
    PAID = "paid"
    TIME_LIMITED = "time_limited"
    # Fallback (UNKNOWN) reasons
    SIGN_ILLEGIBLE = "sign_illegible"
    LOW_CONFIDENCE = "low_confidence"
    PARTIAL_SIGN = "partial_sign"  # params: fields (comma-separated)
    NOTHING_DETECTED = "nothing_detected"
    PAID_HOURS_UNKNOWN = "paid_hours_unknown"
    UNSUPPORTED_CONDITION = "unsupported_condition"  # params: conditions (" | "-separated)
    # Warnings
    PAID_RATE_UNKNOWN = "paid_rate_unknown"
    MAX_DURATION_UNKNOWN = "max_duration_unknown"
    # Location cross-reference (resident permits)
    LOCATION_UNCERTAIN = "location_uncertain"  # params: zone
    ZONE_MISMATCH = "zone_mismatch"  # params: sign_zone, gps_zone
    LOCAL_ZONE_UNKNOWN = "local_zone_unknown"


class PermittedBy(str, Enum):
    """The user attribute that relaxes a restriction for them."""

    DISABLED_PERMIT = "disabled_permit"
    RESIDENT_PERMIT = "resident_permit"  # params: city, zone
    COMMERCIAL_VEHICLE = "commercial_vehicle"


class Reason(BaseModel):
    code: ReasonCode
    message: str = Field(..., description="English, for logs and debugging only.")
    permitted_by: Optional[PermittedBy] = None
    params: Dict[str, str] = Field(default_factory=dict)


class ParkingStatus(str, Enum):
    GREEN = "green"  # allowed, no payment needed
    ORANGE = "orange"  # allowed with conditions (payment and/or time limit)
    RED = "red"  # not allowed
    UNKNOWN = "unknown"  # input insufficient; the engine refuses to guess


class CostType(str, Enum):
    FREE = "free"
    PAID = "paid"
    EXEMPT = "exempt"  # normally paid/restricted, but this user is exempt
    UNKNOWN = "unknown"


class CostInfo(BaseModel):
    type: CostType
    price_per_hour: Optional[float] = None
    currency: str = "ILS"


class UpcomingChange(BaseModel):
    at: datetime
    status: ParkingStatus
    reasons: List[Reason]


class ParkingDecision(BaseModel):
    status: ParkingStatus
    summary: str
    evaluated_at: datetime
    allowed_until: Optional[datetime] = Field(
        None, description="When the user must leave. None = no limit found in the lookahead window."
    )
    max_stay_minutes: Optional[int] = None
    cost: CostInfo
    next_change: Optional[UpcomingChange] = Field(
        None, description="First upcoming change in status or cost (drives reminders)."
    )
    reasons: List[Reason] = Field(default_factory=list)
    warnings: List[Reason] = Field(default_factory=list)
    location: Optional[LocationContext] = Field(None, description="How the GPS fix was resolved, for display.")
