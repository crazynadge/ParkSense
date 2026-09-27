from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.rule_engine import evaluate
from app.schemas import ParkingDecision, ParkingSignData, UserProfile

router = APIRouter(prefix="/api/v1", tags=["parking"])


class AnalyzeParkingRequest(BaseModel):
    sign_data: ParkingSignData = Field(..., description="Extraction result (mocked until Vision is wired in).")
    current_time: datetime = Field(..., description="ISO 8601. Without an offset, Israel local time is assumed.")
    profile: UserProfile
    city: Optional[str] = Field(None, description="Municipality resolved from GPS.")


@router.post("/analyze-parking", response_model=ParkingDecision)
def analyze_parking(request: AnalyzeParkingRequest) -> ParkingDecision:
    return evaluate(request.sign_data, request.current_time, request.profile, request.city)
