import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field, ValidationError

from app.rule_engine import evaluate
from app.schemas import ParkingDecision, ParkingSignData, UserProfile
from app.vision import MockSignExtractor, SignExtractor

router = APIRouter(prefix="/api/v1", tags=["parking"])

MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def get_sign_extractor() -> SignExtractor:
    """Swap for the real Vision implementation once it exists (and override in tests)."""
    return MockSignExtractor()


class AnalyzeParkingRequest(BaseModel):
    sign_data: ParkingSignData = Field(..., description="Extraction result (mocked until Vision is wired in).")
    current_time: datetime = Field(..., description="ISO 8601. Without an offset, Israel local time is assumed.")
    profile: UserProfile
    city: Optional[str] = Field(None, description="Municipality resolved from GPS.")


@router.post("/analyze-parking", response_model=ParkingDecision)
def analyze_parking(request: AnalyzeParkingRequest) -> ParkingDecision:
    """Rule engine only: takes already-extracted sign data. Used for testing and development."""
    return evaluate(request.sign_data, request.current_time, request.profile, request.city)


@router.post("/scan", response_model=ParkingDecision)
async def scan(
    image: UploadFile = File(..., description="Photo of the sign and curb (JPEG, PNG or WebP)."),
    current_time: datetime = Form(..., description="ISO 8601. Without an offset, Israel local time is assumed."),
    profile: str = Form(..., description="UserProfile as a JSON string."),
    city: Optional[str] = Form(None, description="Municipality resolved from GPS."),
    extractor: SignExtractor = Depends(get_sign_extractor),
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

    try:
        user_profile = UserProfile.model_validate_json(profile)
    except ValidationError as e:
        raise HTTPException(422, json.loads(e.json(include_url=False)))

    sign_data = await extractor.extract(data)
    return evaluate(sign_data, current_time, user_profile, city)
