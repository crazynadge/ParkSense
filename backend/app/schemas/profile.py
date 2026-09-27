from enum import Enum
from typing import List

from pydantic import BaseModel, Field

from app.schemas.sign import ResidentZone


class VehicleType(str, Enum):
    PRIVATE = "private"
    COMMERCIAL = "commercial"
    MOTORCYCLE = "motorcycle"


class ResidentPermit(ResidentZone):
    """A resident permit the driver holds. Unlike a sign, the city is mandatory."""

    city: str = Field(..., min_length=1)


class UserProfile(BaseModel):
    vehicle_type: VehicleType = VehicleType.PRIVATE
    resident_permits: List[ResidentPermit] = Field(default_factory=list)
    has_disabled_permit: bool = False
