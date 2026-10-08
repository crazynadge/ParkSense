"""Deterministic point-in-polygon resolution of a GPS fix to city and parking zone."""
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from shapely import prepared
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

from app.schemas.location import GpsFix, LocationContext

DATA_FILE = Path(__file__).resolve().parent / "data" / "geo.json"

# Standing on a boundary street is ambiguous even with a perfect fix.
MIN_BOUNDARY_MARGIN_M = 10.0
# Phones almost always report accuracy; assume a typical urban fix when they don't.
DEFAULT_ACCURACY_M = 50.0
# Beyond this the fix says little about which street you are on: nothing is certain.
MAX_USEFUL_ACCURACY_M = 200.0

# Local equirectangular projection around Gush Dan. Over a few tens of km the
# distance error is well under 1%, far below GPS error.
_LAT0 = math.radians(32.08)
_M_PER_DEG_LAT = 110_574.0
_M_PER_DEG_LON = 111_320.0 * math.cos(_LAT0)


def _to_meters(lon: float, lat: float, z=None):
    return lon * _M_PER_DEG_LON, lat * _M_PER_DEG_LAT


@dataclass(frozen=True)
class _Area:
    id: str
    name_he: Optional[str]
    geometry: BaseGeometry
    prepared: object


@dataclass(frozen=True)
class _Zone:
    city: str
    zone: str
    geometry: BaseGeometry
    prepared: object


class Locator:
    def __init__(self, data: dict) -> None:
        self._cities: List[_Area] = []
        for c in data["cities"]:
            geom = transform(_to_meters, shape(c["geometry"]))
            self._cities.append(_Area(c["id"], c.get("name_he"), geom, prepared.prep(geom)))
        self._zones: List[_Zone] = []
        for z in data["zones"]:
            geom = transform(_to_meters, shape(z["geometry"]))
            self._zones.append(_Zone(z["city"], z["zone"], geom, prepared.prep(geom)))

    @classmethod
    def from_file(cls, path: Path = DATA_FILE) -> "Locator":
        return cls(json.loads(path.read_text()))

    def resolve(self, fix: GpsFix) -> LocationContext:
        accuracy = fix.accuracy_m if fix.accuracy_m is not None else DEFAULT_ACCURACY_M
        point = Point(_to_meters(fix.longitude, fix.latitude))
        error_circle = point.buffer(max(accuracy, MIN_BOUNDARY_MARGIN_M))
        usable = accuracy <= MAX_USEFUL_ACCURACY_M

        containing = [c for c in self._cities if c.prepared.contains(point)]
        # Overlapping sources (official vs OSM) at a shared border: do not pick one.
        city = containing[0] if len(containing) == 1 else None
        if city is not None:
            city_certain = usable and city.prepared.contains(error_circle)
        else:
            # Certainly outside every covered city only if the circle touches none.
            city_certain = usable and not containing and not any(c.prepared.intersects(error_circle) for c in self._cities)

        zone = None
        zone_certain = False
        if city is not None:
            matches = [z for z in self._zones if z.city == city.id and z.prepared.contains(point)]
            if len(matches) == 1:
                zone = matches[0]
                zone_certain = city_certain and zone.prepared.contains(error_circle)

        return LocationContext(
            city=city.id if city else None,
            city_name_he=city.name_he if city else None,
            city_certain=city_certain,
            zone=zone.zone if zone else None,
            zone_certain=zone_certain,
            accuracy_m=fix.accuracy_m,
            source=fix.source,
        )


@lru_cache
def get_locator() -> Locator:
    return Locator.from_file()
