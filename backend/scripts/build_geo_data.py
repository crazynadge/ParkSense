"""Build app/geo/data/geo.json: municipal boundaries and resident parking zones.

Sources:
- Tel Aviv-Yafo city boundary and parking zones: Tel Aviv municipality GIS
  (IView2 MapServer layers 890 "גבול העיר" and 544 "אזורי חניה"), reprojected
  server-side from EPSG:2039 to WGS84.
- Neighbouring municipal boundaries: OpenStreetMap via Nominatim
  (© OpenStreetMap contributors, ODbL 1.0).

Usage (from backend/):  .venv/bin/python -m scripts.build_geo_data
"""
import json
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

from shapely.geometry import mapping, shape
from shapely.validation import make_valid

OUT = Path(__file__).resolve().parents[1] / "app" / "geo" / "data" / "geo.json"
TLV_GIS = "https://gisn.tel-aviv.gov.il/arcgis/rest/services/IView2/MapServer"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "ParkSense-geo-data-build/0.1"

TEL_AVIV = {"id": "Tel Aviv", "name_he": "תל אביב-יפו"}
# (id, English query, OSM relation id expected) — the id guards against Nominatim
# silently returning a different place.
NEIGHBOURS = [
    ("Givatayim", "Givatayim", 1382923),
    ("Ramat Gan", "Ramat Gan", 1382493),
    ("Bnei Brak", "Bnei Brak", 1382817),
    ("Holon", "Holon", 1382460),
    ("Bat Yam", "Bat Yam", 1382458),
    ("Herzliya", "Herzliya", 1382820),
    ("Ramat HaSharon", "Ramat HaSharon", 1382821),
]


def fetch_json(url: str, params: dict) -> object:
    request = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def tlv_layer(layer: int) -> list:
    data = fetch_json(
        f"{TLV_GIS}/{layer}/query",
        {"where": "1=1", "outFields": "*", "returnGeometry": "true", "outSR": "4326", "f": "geojson"},
    )
    return data["features"]


def clean(geometry: dict) -> dict:
    geom = make_valid(shape(geometry))
    if geom.geom_type not in ("Polygon", "MultiPolygon"):
        geom = geom.buffer(0)
    return mapping(geom)


def main() -> None:
    [boundary] = tlv_layer(890)
    cities = [{**TEL_AVIV, "source": "tel-aviv-gis:890", "geometry": clean(boundary["geometry"])}]

    zones = [
        {
            "city": TEL_AVIV["id"],
            "zone": str(f["properties"]["ms_ezor"]),
            "source": f"tel-aviv-gis:544 (imported {f['properties']['date_import']})",
            "geometry": clean(f["geometry"]),
        }
        for f in tlv_layer(544)
    ]

    for city_id, query, relation_id in NEIGHBOURS:
        time.sleep(1.1)  # Nominatim usage policy: at most 1 request per second
        results = fetch_json(
            NOMINATIM,
            {"q": f"{query}, Israel", "format": "jsonv2", "polygon_geojson": 1, "limit": 5, "accept-language": "he"},
        )
        match = [r for r in results if r.get("osm_type") == "relation" and r.get("osm_id") == relation_id]
        if not match:
            raise SystemExit(f"OSM relation {relation_id} for {city_id} not found; check before trusting the data")
        cities.append(
            {
                "id": city_id,
                "name_he": match[0]["name"],
                "source": f"osm:relation/{relation_id}",
                "geometry": clean(match[0]["geojson"]),
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "generated": date.today().isoformat(),
                "attribution": "Tel Aviv-Yafo Municipality GIS; © OpenStreetMap contributors (ODbL 1.0)",
                "cities": cities,
                "zones": sorted(zones, key=lambda z: int(z["zone"])),
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB): {len(cities)} cities, {len(zones)} zones")


if __name__ == "__main__":
    main()
