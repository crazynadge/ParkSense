"""Run the real Vision extractor on photos and print what it read and what the engine decides.

Usage (from backend/):
    .venv/bin/python -m scripts.try_vision photo.jpg [...] --lat 32.0753 --lon 34.7747 [--accuracy 10]
        [--permit "Tel Aviv:2"] [--at 2026-09-28T10:00]
"""
import argparse
import asyncio
import json
import mimetypes
import time
from datetime import datetime
from pathlib import Path

from app.config import get_settings
from app.geo import get_locator
from app.rule_engine import evaluate
from app.rule_engine.policy import DEFAULT_TIMEZONE
from app.schemas import GpsFix, ResidentPermit, UserProfile
from app.vision.gemini import GeminiSignExtractor


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--lat", type=float, help="Where the photo was taken (omit to test without GPS)")
    parser.add_argument("--lon", type=float)
    parser.add_argument("--accuracy", type=float, default=10.0, help="GPS accuracy in meters")
    parser.add_argument("--permit", action="append", default=[], help='Resident permit "City:zone", repeatable')
    parser.add_argument("--at", help="Local time, ISO 8601 (default: now)")
    args = parser.parse_args()

    settings = get_settings()
    if settings.vision_provider != "gemini":
        raise SystemExit("Set VISION_PROVIDER=gemini in backend/.env to try the real extractor.")
    extractor = GeminiSignExtractor(settings.gemini_api_key, settings.gemini_model, settings.gemini_timeout_seconds)
    now = datetime.fromisoformat(args.at) if args.at else datetime.now(DEFAULT_TIMEZONE)
    location = None
    if args.lat is not None and args.lon is not None:
        location = get_locator().resolve(GpsFix(latitude=args.lat, longitude=args.lon, accuracy_m=args.accuracy))
        print("location:", location.model_dump(exclude_none=True))
    permits = [ResidentPermit(city=c, zone=z) for c, z in (p.rsplit(":", 1) for p in args.permit)]
    profile = UserProfile(resident_permits=permits)

    for path in args.images:
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        started = time.perf_counter()
        sign = await extractor.extract(path.read_bytes(), mime)
        elapsed = time.perf_counter() - started
        decision = evaluate(sign, now, profile, location)

        print(f"\n=== {path.name}  ({settings.gemini_model}, {elapsed:.2f}s)")
        print(json.dumps(sign.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2))
        print(f"-> {decision.status.value}: {[r.message for r in decision.reasons]}")
        if decision.allowed_until:
            print(f"   allowed until {decision.allowed_until:%a %H:%M}, cost {decision.cost.type.value}")


if __name__ == "__main__":
    asyncio.run(main())
