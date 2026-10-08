import asyncio
import json
from datetime import datetime
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from google.genai import errors

from app.api.v1.routes import get_sign_extractor
from app.config import get_settings
from app.main import app
from app.rule_engine import evaluate
from app.rule_engine.policy import DEFAULT_TIMEZONE
from app.schemas import CurbMarking, LocationContext, ParkingStatus, ReasonCode, RuleType, UserProfile, Weekday
from app.vision import VisionUnavailableError
from app.vision.extraction_schema import SignExtraction
from app.vision.gemini import GeminiSignExtractor

MONDAY_10AM = datetime(2026, 9, 28, 10, 0, tzinfo=DEFAULT_TIMEZONE)
VISITOR = UserProfile()


def extraction(**overrides) -> dict:
    """A well-formed model response for a Tel Aviv blue-white sign."""
    base = {
        "sign_detected": True,
        "is_legible": True,
        "confidence": 0.93,
        "curb_marking": "blue_white",
        "rules": [
            {
                "rule_type": "paid",
                "windows": [
                    {"days": ["sun", "mon", "tue", "wed", "thu"], "start": "08:00", "end": "19:00"},
                    {"days": ["fri"], "start": "08:00", "end": "13:00"},
                ],
                "max_duration_minutes": None,
                "price_per_hour": 6.3,
                "exempt_resident_zones": ["2"],
                "exempt_local_zone": False,
                "exempt_disabled": None,
                "raw_text": "חניה בתשלום א'-ה' 08:00-19:00 ו' 08:00-13:00 למעט בעלי תו אזור 2",
            }
        ],
        "unreadable_fields": [],
        "unsupported_conditions": [],
        "free_outside_windows": False,
    }
    base.update(overrides)
    return base


class FakeModels:
    def __init__(self, text=None, error=None):
        self.text, self.error, self.calls = text, error, []

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.text, prompt_feedback=None)


def make_extractor(text=None, error=None):
    extractor = GeminiSignExtractor(api_key="test-key", model="gemini-test", timeout_seconds=5)
    models = FakeModels(text=text, error=error)
    extractor._client = SimpleNamespace(aio=SimpleNamespace(models=models))
    return extractor, models


def run(coro):
    return asyncio.run(coro)


class TestSuccessfulExtraction:
    def test_valid_output_becomes_engine_input(self):
        extractor, models = make_extractor(json.dumps(extraction()))
        sign = run(extractor.extract(b"jpeg-bytes"))

        assert sign.curb_marking == CurbMarking.BLUE_WHITE
        [rule] = sign.rules
        assert rule.rule_type == RuleType.PAID
        assert rule.windows[1].days == [Weekday.FRI]
        assert rule.windows[1].end.hour == 13
        assert rule.exempt_resident_zones[0].zone == "2"
        # City is never taken from the model; the engine resolves it from GPS.
        assert rule.exempt_resident_zones[0].city is None

        decision = evaluate(sign, MONDAY_10AM, VISITOR, LocationContext(city="Tel Aviv", city_certain=True))
        assert decision.status == ParkingStatus.ORANGE
        assert decision.cost.price_per_hour == 6.3

    def test_request_sends_image_schema_and_deterministic_settings(self):
        extractor, models = make_extractor(json.dumps(extraction()))
        run(extractor.extract(b"png-bytes", "image/png"))

        [call] = models.calls
        assert call["model"] == "gemini-test"
        image_part = call["contents"][0]
        assert image_part.inline_data.data == b"png-bytes"
        assert image_part.inline_data.mime_type == "image/png"
        config = call["config"]
        assert config.response_mime_type == "application/json"
        assert config.response_json_schema == SignExtraction.model_json_schema()
        assert config.temperature == 0

    def test_schema_is_plain_json(self):
        json.dumps(SignExtraction.model_json_schema())


class TestUntrustworthyOutputBecomesUnknown:
    @pytest.mark.parametrize(
        "text",
        [
            "not json at all",
            json.dumps({"sign_detected": True}),  # missing required fields
            json.dumps(extraction(confidence=1.7)),  # out of range
            json.dumps(extraction(curb_marking="purple")),  # not an enum value
        ],
    )
    def test_malformed_output(self, text):
        extractor, _ = make_extractor(text)
        sign = run(extractor.extract(b"x"))
        assert evaluate(sign, MONDAY_10AM, VISITOR).status == ParkingStatus.UNKNOWN

    def test_self_contradictory_window(self):
        bad = extraction()
        bad["rules"][0]["windows"] = [{"days": [], "start": "08:00", "end": "08:00"}]
        extractor, _ = make_extractor(json.dumps(bad))
        sign = run(extractor.extract(b"x"))
        assert evaluate(sign, MONDAY_10AM, VISITOR).status == ParkingStatus.UNKNOWN

    def test_invalid_time_format(self):
        bad = extraction()
        bad["rules"][0]["windows"][0]["start"] = "8am"
        extractor, _ = make_extractor(json.dumps(bad))
        assert evaluate(run(extractor.extract(b"x")), MONDAY_10AM, VISITOR).status == ParkingStatus.UNKNOWN

    def test_unsupported_condition_is_reported_not_dropped(self):
        extractor, _ = make_extractor(json.dumps(extraction(unsupported_conditions=["למעט ערבי חג"])))
        decision = evaluate(run(extractor.extract(b"x")), MONDAY_10AM, VISITOR)
        assert decision.status == ParkingStatus.UNKNOWN
        assert decision.reasons[0].code == ReasonCode.UNSUPPORTED_CONDITION
        assert decision.reasons[0].params == {"conditions": "למעט ערבי חג"}


class TestProviderFailures:
    @pytest.mark.parametrize(
        "error",
        [
            errors.ClientError(403, {"error": {"code": 403, "message": "API key not valid"}}),
            errors.ServerError(503, {"error": {"code": 503, "message": "overloaded"}}),
            httpx.ReadTimeout("timed out"),
            httpx.ConnectError("no route"),
        ],
    )
    def test_raises_vision_unavailable(self, error):
        extractor, _ = make_extractor(error=error)
        with pytest.raises(VisionUnavailableError):
            run(extractor.extract(b"x"))

    def test_empty_response(self):
        extractor, _ = make_extractor(text="")
        with pytest.raises(VisionUnavailableError):
            run(extractor.extract(b"x"))

    def test_scan_endpoint_returns_503(self):
        class DownExtractor:
            async def extract(self, image, mime_type="image/jpeg"):
                raise VisionUnavailableError("down")

        app.dependency_overrides[get_sign_extractor] = DownExtractor
        try:
            response = TestClient(app).post(
                "/api/v1/scan",
                files={"image": ("s.jpg", b"\xff\xd8\xff", "image/jpeg")},
                data={"current_time": "2026-09-28T10:00:00+03:00", "profile": "{}"},
            )
        finally:
            app.dependency_overrides.clear()
        assert response.status_code == 503


class TestConfig:
    @pytest.fixture(autouse=True)
    def fresh_settings(self, monkeypatch):
        get_settings.cache_clear()
        yield monkeypatch
        get_settings.cache_clear()

    def test_gemini_without_key_refuses_to_start(self, fresh_settings):
        fresh_settings.setenv("VISION_PROVIDER", "gemini")
        fresh_settings.setenv("GEMINI_API_KEY", "")
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            get_settings()

    def test_unknown_provider_rejected(self, fresh_settings):
        fresh_settings.setenv("VISION_PROVIDER", "tesseract")
        with pytest.raises(RuntimeError, match="VISION_PROVIDER"):
            get_settings()

    def test_gemini_with_key(self, fresh_settings):
        fresh_settings.setenv("VISION_PROVIDER", "gemini")
        fresh_settings.setenv("GEMINI_API_KEY", "abc")
        fresh_settings.setenv("GEMINI_MODEL", "gemini-x")
        settings = get_settings()
        assert (settings.vision_provider, settings.gemini_api_key, settings.gemini_model) == ("gemini", "abc", "gemini-x")


class TestFreeOutsideWindows:
    def test_flag_reaches_engine_and_gives_definitive_verdict(self):
        extractor, _ = make_extractor(json.dumps(extraction(free_outside_windows=True)))
        sign = run(extractor.extract(b"x"))
        assert sign.free_outside_windows
        # Saturday: outside every listed window -> free per the sign, not "unknown".
        saturday = datetime(2026, 10, 3, 12, 0, tzinfo=DEFAULT_TIMEZONE)
        decision = evaluate(sign, saturday, VISITOR)
        assert decision.status == ParkingStatus.GREEN
        assert decision.reasons[0].code == ReasonCode.FREE_OUTSIDE_HOURS

    def test_contradiction_with_always_on_rule_is_unknown(self):
        bad = extraction(free_outside_windows=True)
        bad["rules"][0]["windows"] = []  # "applies at all times" AND "free the rest of the time"
        extractor, _ = make_extractor(json.dumps(bad))
        assert evaluate(run(extractor.extract(b"x")), MONDAY_10AM, VISITOR).status == ParkingStatus.UNKNOWN
