"""Locator tests against the real boundary data in app/geo/data/geo.json."""
import json

import pytest
from shapely.geometry import shape

from app.geo import get_locator
from app.geo.locator import DATA_FILE, MAX_USEFUL_ACCURACY_M
from app.schemas import GpsFix


def resolve(lat, lon, accuracy_m=10.0):
    return get_locator().resolve(GpsFix(latitude=lat, longitude=lon, accuracy_m=accuracy_m))


def shared_border_midpoint(a, b):
    """A point on the common boundary of two polygons, taken from the data itself."""
    border = a.boundary.intersection(b.boundary)
    assert border.length > 0, "areas do not share a border"
    point = border.interpolate(0.5, normalized=True)
    return point.y, point.x


@pytest.fixture(scope="module")
def data():
    return json.loads(DATA_FILE.read_text())


@pytest.mark.parametrize(
    "lat, lon, city, zone",
    [
        (32.0753, 34.7747, "Tel Aviv", "9"),  # Dizengoff Center
        (32.0548, 34.7562, "Tel Aviv", "1"),  # Jaffa Clock Tower
        (32.0744, 34.7920, "Tel Aviv", "7"),  # Azrieli Center
        (32.1133, 34.8044, "Tel Aviv", "12"),  # Tel Aviv University
        (32.0720, 34.8110, "Givatayim", None),  # Givatayim Mall
        (32.0835, 34.8025, "Ramat Gan", None),  # Diamond Exchange
        (32.0170, 34.7500, "Bat Yam", None),
    ],
)
def test_landmarks(lat, lon, city, zone):
    loc = resolve(lat, lon)
    assert (loc.city, loc.zone) == (city, zone)
    assert loc.city_certain
    assert loc.zone_certain == (zone is not None)


def test_hebrew_city_name():
    assert resolve(32.0753, 34.7747).city_name_he == "תל אביב-יפו"


def test_at_sea_is_certainly_no_city():
    loc = resolve(32.08, 34.74)
    assert loc.city is None and loc.city_certain


def test_poor_accuracy_is_never_certain():
    loc = resolve(32.0753, 34.7747, accuracy_m=MAX_USEFUL_ACCURACY_M + 1)
    assert loc.city == "Tel Aviv"  # best estimate, reported for display
    assert not loc.city_certain and not loc.zone_certain


def test_missing_accuracy_uses_conservative_default():
    loc = get_locator().resolve(GpsFix(latitude=32.0753, longitude=34.7747))
    assert loc.zone == "9" and loc.accuracy_m is None


def test_zone_boundary_is_uncertain(data):
    zones = {z["zone"]: shape(z["geometry"]) for z in data["zones"]}
    lat, lon = shared_border_midpoint(zones["2"], zones["4"])
    loc = resolve(lat, lon, accuracy_m=5)
    assert loc.city == "Tel Aviv" and loc.city_certain
    assert not loc.zone_certain


def test_accuracy_circle_crossing_zone_boundary_is_uncertain():
    # 32.052735,34.784532 lies on the 2|4 border; 150 m north is inside a zone but
    # a 300 m error circle still reaches across.
    assert not resolve(32.052735 + 0.00135, 34.784532, accuracy_m=300).zone_certain


def test_city_border_is_uncertain(data):
    # Official (Tel Aviv GIS) and OSM (Givatayim) borders differ by ~1 m slivers, so there
    # is no single shared line; take the point on Tel Aviv's border closest to Givatayim.
    cities = {c["id"]: shape(c["geometry"]) for c in data["cities"]}
    givatayim_center = cities["Givatayim"].representative_point()
    border = cities["Tel Aviv"].boundary
    point = border.interpolate(border.project(givatayim_center))
    loc = resolve(point.y, point.x, accuracy_m=5)
    assert not loc.city_certain
    assert not loc.zone_certain


def test_zones_tile_tel_aviv_without_overlap(data):
    zones = [shape(z["geometry"]) for z in data["zones"]]
    for i, a in enumerate(zones):
        for b in zones[i + 1 :]:
            assert a.intersection(b).area < 1e-9
