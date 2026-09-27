"""Runtime settings from environment variables (and backend/.env in development)."""
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

VISION_PROVIDERS = ("gemini", "mock")


@dataclass(frozen=True)
class Settings:
    vision_provider: str
    gemini_api_key: Optional[str]
    gemini_model: str
    gemini_timeout_seconds: float


@lru_cache
def get_settings() -> Settings:
    settings = Settings(
        vision_provider=os.getenv("VISION_PROVIDER", "gemini").strip().lower(),
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        gemini_timeout_seconds=float(os.getenv("GEMINI_TIMEOUT_SECONDS", "8")),
    )
    if settings.vision_provider not in VISION_PROVIDERS:
        raise RuntimeError(f"VISION_PROVIDER must be one of {VISION_PROVIDERS}, got {settings.vision_provider!r}")
    # Never fall back to the mock silently: it returns a fabricated sign.
    if settings.vision_provider == "gemini" and not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to backend/.env, or set VISION_PROVIDER=mock for offline development."
        )
    return settings
