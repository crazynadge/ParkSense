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
curl -X POST localhost:8000/api/v1/analyze-parking \
  -H 'Content-Type: application/json' -d @examples/tel_aviv_visitor_weekday.json
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

**Hebrew / RTL:** RTL is forced through the `expo-localization` plugin in `app.json`.
This applies in development builds (`npx expo run:ios|android`) and store builds, and
on web (via `<html dir="rtl">`). **Expo Go ignores it** and shows a left-to-right layout.
Start Hebrew UI strings with a Hebrew word: a string that begins with Latin text
(e.g. "ParkSense") gets a left-to-right base direction and scrambles the sentence.
