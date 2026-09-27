import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
EXAMPLES = Path(__file__).parent.parent / "examples"


def test_health():
    assert client.get("/health").json() == {"status": "ok", "vision_provider": "mock"}


def test_analyze_parking_example_request():
    payload = json.loads((EXAMPLES / "tel_aviv_visitor_weekday.json").read_text())
    response = client.post("/api/v1/analyze-parking", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "orange"
    assert body["cost"] == {"type": "paid", "price_per_hour": 6.3, "currency": "ILS"}
    assert body["allowed_until"].startswith("2026-09-28T19:00:00")
    assert body["reasons"] == [{"code": "paid", "message": "Paid parking", "permitted_by": None, "params": {}}]


def test_invalid_payload_is_rejected():
    response = client.post("/api/v1/analyze-parking", json={"sign_data": {}, "profile": {}})
    assert response.status_code == 422
