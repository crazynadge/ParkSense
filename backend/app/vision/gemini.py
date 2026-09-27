"""Gemini implementation of SignExtractor."""
import logging

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from app.schemas.sign import ParkingSignData
from app.vision.errors import VisionUnavailableError
from app.vision.extraction_schema import SignExtraction, to_sign_data, unreadable_result
from app.vision.prompt import SYSTEM_INSTRUCTION, USER_PROMPT

logger = logging.getLogger(__name__)


class GeminiSignExtractor:
    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
        )
        self._model = model
        self._config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_json_schema=SignExtraction.model_json_schema(),
            temperature=0,
            # Transcription, not reasoning: keep latency inside the PRD's ~3 s budget.
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
        )

    async def extract(self, image: bytes, mime_type: str = "image/jpeg") -> ParkingSignData:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=[types.Part.from_bytes(data=image, mime_type=mime_type), USER_PROMPT],
                config=self._config,
            )
        except errors.ClientError as e:
            # 4xx: our request or configuration is wrong (bad key, bad model name, quota).
            logger.error("Gemini rejected the request: %s", e)
            raise VisionUnavailableError("Vision request rejected") from e
        except Exception as e:  # network errors, timeouts, 5xx
            logger.warning("Gemini unavailable: %s", e)
            raise VisionUnavailableError("Vision service unavailable") from e

        text = response.text
        if not text:
            logger.warning("Gemini returned no content: %s", response.prompt_feedback)
            raise VisionUnavailableError("Vision service returned no content")

        try:
            return to_sign_data(SignExtraction.model_validate_json(text))
        except ValidationError as e:
            # Malformed or self-contradictory output: refuse to guess.
            logger.warning("Discarding invalid extraction: %s | output: %s", e, text[:2000])
            return unreadable_result()
