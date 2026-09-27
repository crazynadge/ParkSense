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

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0
# Rule engine only, with pre-extracted sign data:
curl -X POST localhost:8000/api/v1/analyze-parking \
  -H 'Content-Type: application/json' -d @examples/tel_aviv_visitor_weekday.json
# Full pipeline, photo -> Vision (mock for now) -> rule engine:
curl -X POST localhost:8000/api/v1/scan -F image=@sign.jpg \
  -F current_time=2026-09-28T10:00:00+03:00 -F city="Tel Aviv" \
  -F 'profile={"vehicle_type":"private","resident_permits":[],"has_disabled_permit":false}'
```

Interactive docs: http://localhost:8000/docs

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
