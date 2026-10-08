import json

from fastapi.testclient import TestClient

from app.api.v1.routes import get_sign_extractor
from app.main import app
from app.schemas import CurbMarking, ParkingSignData

client = TestClient(app)

PROFILE = json.dumps({"vehicle_type": "private", "resident_permits": [], "has_disabled_permit": False})
FAKE_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100


IN_TLV_ZONE_2 = {"latitude": "32.049083", "longitude": "34.774115", "accuracy_m": "12"}


def post_scan(image=FAKE_JPEG, content_type="image/jpeg", profile=PROFILE, location=IN_TLV_ZONE_2):
    return client.post(
        "/api/v1/scan",
        files={"image": ("sign.jpg", image, content_type)},
        data={"current_time": "2026-09-28T10:00:00+03:00", "profile": profile, **location},
    )


def test_scan_runs_extractor_then_rule_engine():
    response = post_scan()
    assert response.status_code == 200
    body = response.json()
    # MockSignExtractor returns the Tel Aviv blue-white sign: paid on Monday 10:00.
    assert body["status"] == "orange"
    assert body["cost"]["type"] == "paid"


def test_scan_passes_image_bytes_to_extractor():
    received = []

    class RecordingExtractor:
        async def extract(self, image: bytes, mime_type: str = "image/jpeg") -> ParkingSignData:
            received.append((image, mime_type))
            return ParkingSignData(sign_detected=False, confidence=0.9, curb_marking=CurbMarking.RED_WHITE)

    app.dependency_overrides[get_sign_extractor] = RecordingExtractor
    try:
        response = post_scan()
    finally:
        app.dependency_overrides.clear()
    assert received == [(FAKE_JPEG, "image/jpeg")]
    assert response.json()["status"] == "red"


def test_rejects_non_image():
    assert post_scan(content_type="application/pdf").status_code == 415


def test_rejects_empty_image():
    assert post_scan(image=b"").status_code == 400


def test_rejects_oversized_image():
    assert post_scan(image=b"\x00" * (10 * 1024 * 1024 + 1)).status_code == 413


def test_rejects_invalid_profile():
    response = post_scan(profile='{"vehicle_type": "spaceship"}')
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["vehicle_type"]


def test_gps_is_resolved_and_echoed():
    location = post_scan().json()["location"]
    assert location == {
        "city": "Tel Aviv",
        "city_name_he": "תל אביב-יפו",
        "city_certain": True,
        "zone": "2",
        "zone_certain": True,
        "accuracy_m": 12.0,
        "source": "live",
    }


def test_parked_location_source_is_echoed():
    body = post_scan(location={**IN_TLV_ZONE_2, "location_source": "parked"}).json()
    assert body["location"]["source"] == "parked"
    assert body["location"]["zone"] == "2"


def test_unknown_location_source_rejected():
    assert post_scan(location={**IN_TLV_ZONE_2, "location_source": "guess"}).status_code == 422


def test_resident_permit_uses_gps_zone():
    resident = json.dumps({"resident_permits": [{"city": "Tel Aviv", "zone": "2"}]})
    body = post_scan(profile=resident).json()
    # MockSignExtractor: paid, zone 2 exempt; GPS confirms zone 2.
    assert body["status"] == "green"
    assert body["cost"]["type"] == "exempt"


def test_scan_without_location():
    response = post_scan(location={})
    assert response.status_code == 200
    assert response.json()["location"] is None


def test_latitude_without_longitude_rejected():
    assert post_scan(location={"latitude": "32.08"}).status_code == 422


def test_out_of_range_coordinates_rejected():
    assert post_scan(location={"latitude": "132.0", "longitude": "34.77"}).status_code == 422
