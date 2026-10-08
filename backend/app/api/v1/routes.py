import json
import logging
from datetime import datetime
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field, ValidationError

from app.config import get_settings
from app.geo import Locator, get_locator
from app.rule_engine import evaluate
from app.schemas import GpsFix, LocationContext, ParkingDecision, ParkingSignData, UserProfile
from app.schemas.location import LocationSource
from app.vision import MockSignExtractor, SignExtractor, VisionUnavailableError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["parking"])

MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@lru_cache
def get_sign_extractor() -> SignExtractor:
    """One shared extractor per process (the Gemini client pools connections). Override in tests."""
    settings = get_settings()
    if settings.vision_provider == "mock":
        logger.warning("VISION_PROVIDER=mock: /scan returns a fixed, fabricated sign")
        return MockSignExtractor()
    from app.vision.gemini import GeminiSignExtractor

    assert settings.gemini_api_key  # enforced by get_settings
    return GeminiSignExtractor(settings.gemini_api_key, settings.gemini_model, settings.gemini_timeout_seconds)


def _resolve(locator: Locator, fix: Optional[GpsFix]) -> Optional[LocationContext]:
    return locator.resolve(fix) if fix else None


class AnalyzeParkingRequest(BaseModel):
    sign_data: ParkingSignData = Field(..., description="Already-extracted sign data.")
    current_time: datetime = Field(..., description="ISO 8601. Without an offset, Israel local time is assumed.")
    profile: UserProfile
    location: Optional[GpsFix] = Field(None, description="Device GPS fix; omitted if unavailable.")


@router.post("/analyze-parking", response_model=ParkingDecision)
def analyze_parking(request: AnalyzeParkingRequest, locator: Locator = Depends(get_locator)) -> ParkingDecision:
    """Rule engine only: takes already-extracted sign data. Used for testing and development."""
    location = _resolve(locator, request.location)
    return evaluate(request.sign_data, request.current_time, request.profile, location)


@router.post("/scan", response_model=ParkingDecision)
async def scan(
    image: UploadFile = File(..., description="Photo of the sign and curb (JPEG, PNG or WebP)."),
    current_time: datetime = Form(..., description="ISO 8601. Without an offset, Israel local time is assumed."),
    profile: str = Form(..., description="UserProfile as a JSON string."),
    latitude: Optional[float] = Form(None, ge=-90, le=90),
    longitude: Optional[float] = Form(None, ge=-180, le=180),
    accuracy_m: Optional[float] = Form(None, ge=0, description="GPS horizontal accuracy in meters."),
    location_source: LocationSource = Form("live", description="live, or parked (the car's saved position)."),
    extractor: SignExtractor = Depends(get_sign_extractor),
    locator: Locator = Depends(get_locator),
) -> ParkingDecision:
    """Full pipeline: image -> Vision extraction -> deterministic rule engine.

    The image is processed in memory only and never persisted.
    """
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(415, f"Unsupported image type: {image.content_type}")
    data = await image.read(MAX_IMAGE_BYTES + 1)
    if not data:
        raise HTTPException(400, "Empty image")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Image exceeds %d MB" % (MAX_IMAGE_BYTES // (1024 * 1024)))

    if (latitude is None) != (longitude is None):
        raise HTTPException(422, "latitude and longitude must be sent together")
    fix = (
        GpsFix(latitude=latitude, longitude=longitude, accuracy_m=accuracy_m, source=location_source)
        if latitude is not None
        else None
    )

    try:
        user_profile = UserProfile.model_validate_json(profile)
    except ValidationError as e:
        raise HTTPException(422, json.loads(e.json(include_url=False)))

    try:
        sign_data = await extractor.extract(data, image.content_type)
    except VisionUnavailableError:
        raise HTTPException(503, "Sign recognition is temporarily unavailable")
    return evaluate(sign_data, current_time, user_profile, _resolve(locator, fix))
