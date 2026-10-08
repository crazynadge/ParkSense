# ParkSense

"Can I park here, right now, for how long, and at what cost?"

```
frontend/   Expo (React Native, TypeScript) mobile app
backend/    FastAPI server
  app/schemas/      Pydantic contract: sign extraction, user profile, decision
  app/vision/       AI extraction (image -> ParkingSignData). Mock only for now.
  app/rule_engine/  Deterministic decision logic. Never imports app.vision.
  app/api/v1/       HTTP routes
  examples/         Sample request payloads
```

## Backend

Requires Python 3.10+ (3.12 recommended). On macOS 26.0.x, Homebrew's `python@3.12`
has a broken `pyexpat`; use [uv](https://docs.astral.sh/uv/)'s standalone Python instead.

```bash
cd backend
uv venv --python 3.12 --python-preference only-managed .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
cp .env.example .env    # then paste your GEMINI_API_KEY
.venv/bin/pytest
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0
# Rule engine only, with pre-extracted sign data:
curl -X POST localhost:8000/api/v1/analyze-parking \
  -H 'Content-Type: application/json' -d @examples/tel_aviv_visitor_weekday.json
# Full pipeline, photo -> Vision (mock for now) -> rule engine:
curl -X POST localhost:8000/api/v1/scan -F image=@sign.jpg \
  -F current_time=2026-09-28T10:00:00+03:00 -F latitude=32.0753 -F longitude=34.7747 -F accuracy_m=10 \
  -F 'profile={"vehicle_type":"private","resident_permits":[],"has_disabled_permit":false}'
```

Interactive docs: http://localhost:8000/docs

**Vision:** `VISION_PROVIDER=gemini` (default) calls Gemini Flash; the server refuses to start
without `GEMINI_API_KEY`. `VISION_PROVIDER=mock` returns a fixed, fabricated sign for offline
work. `/health` reports which one is active. To see what Gemini reads from real photos:

```bash
.venv/bin/python -m scripts.try_vision photo.jpg --lat 32.0753 --lon 34.7747 [--permit "Tel Aviv:9"]
```

**Location:** the app sends the device's GPS fix with each scan. `app/geo` resolves it by
point-in-polygon against `app/geo/data/geo.json` to a city and resident parking zone, and marks
each *certain* only if the whole GPS error circle lies inside it (so boundary streets are
reported as uncertain, never guessed). The rule engine then cross-checks: resident permits need
a certain city; a sign zone that contradicts a certain GPS zone is treated as a possible misread;
"local residents" signs without a zone number take the zone from GPS.

**חניתי כאן (Parked here):** the Home screen can pin the car's position (a precise fix, stored
in the iOS Keychain / Android Keystore via `expo-secure-store`, device-only, expiring after 24 h).
While a spot is saved, scans are judged by the car's position, not where the photo is taken, and
the result says so. On web (development only) the spot is kept in memory.

Boundary data: Tel Aviv-Yafo city boundary and parking zones from the municipality GIS
(layers 890, 544); neighbouring cities from © OpenStreetMap contributors (ODbL). Rebuild with:

```bash
.venv/bin/python -m scripts.build_geo_data
```

Gemini only transcribes the sign into JSON. Anything malformed or self-contradictory becomes
`unknown`, and conditions the schema cannot express (e.g. holiday eves) are surfaced as
`unsupported_condition` instead of being dropped.

## Frontend

```bash
cd frontend
npm install
npx expo start        # then scan the QR code with Expo Go, or press i / a / w
npx tsc --noEmit && npx expo lint
```

Navigation uses Expo Router; every file in `frontend/src/app/` is a screen.

**Reaching the backend:** the app calls `http://<your Mac's LAN IP>:8000` (taken from
the Metro dev server address), so a phone on the same Wi-Fi can reach it. Start the
backend with `--host 0.0.0.0` for that to work. Override with `EXPO_PUBLIC_API_URL`.

**Camera:** works in Expo Go on a physical device (the iOS Simulator has no camera). Photos
are downscaled to 1600px and uploaded to `/api/v1/scan`; they are not stored. In development
builds, Home also links to *תרחישים לדוגמה*, which sends hand-written sign data straight to the
rule engine to exercise every result state.

**Hebrew / RTL:** RTL is forced through the `expo-localization` plugin in `app.json`.
This applies in development builds (`npx expo run:ios|android`) and store builds, and
on web (via `<html dir="rtl">`). **Expo Go ignores it** and shows a left-to-right layout.
Start Hebrew UI strings with a Hebrew word: a string that begins with Latin text
(e.g. "ParkSense") gets a left-to-right base direction and scrambles the sentence.
