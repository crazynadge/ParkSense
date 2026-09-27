from typing import Optional

from pydantic import BaseModel, Field


class GpsFix(BaseModel):
    """Raw device location, as sent by the app."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy_m: Optional[float] = Field(None, ge=0, description="Horizontal accuracy radius in meters.")


class LocationContext(BaseModel):
    """A GPS fix resolved against municipal and parking-zone boundaries.

    "Certain" means the whole GPS error circle lies inside that area, so the answer
    cannot flip within the device's stated accuracy. At a boundary street the
    engine therefore gets an honest "uncertain" rather than a coin flip.
    """

    city: Optional[str] = Field(None, description="Canonical city id containing the fix, if any.")
    city_name_he: Optional[str] = None
    city_certain: bool = False
    zone: Optional[str] = Field(None, description="Resident parking zone containing the fix, if known.")
    zone_certain: bool = False
    accuracy_m: Optional[float] = None
