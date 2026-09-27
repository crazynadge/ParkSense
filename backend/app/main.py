from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import router as v1_router
from app.config import get_settings

# Fail at startup, not on the first scan, if Vision is misconfigured.
settings = get_settings()

app = FastAPI(title="ParkSense API", version="0.1.0")

# Permissive for local development with Expo; restrict before deploying.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(v1_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "vision_provider": settings.vision_provider}
