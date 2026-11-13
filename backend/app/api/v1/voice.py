"""Browser speech provider discovery and optional private ElevenLabs synthesis."""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from app.api.v1.deps import get_current_user
from app.core.config import secret_value, settings

router = APIRouter(prefix="/voice", tags=["Voice"])


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@router.get("/status")
def voice_status():
    provider = settings.VOICE_PROVIDER.lower()
    if provider == "browser":
        return {"provider": "browser", "speech_synthesis": True, "server_synthesis": False}
    if provider == "elevenlabs":
        return {"provider": "elevenlabs", "speech_synthesis": bool(secret_value(settings.ELEVENLABS_API_KEY) and settings.ELEVENLABS_VOICE_ID), "server_synthesis": True}
    return {"provider": provider, "speech_synthesis": False, "server_synthesis": False}


@router.post("/speech")
async def synthesize(payload: SpeechRequest, _user=Depends(get_current_user)):
    if settings.VOICE_PROVIDER.lower() != "elevenlabs":
        raise HTTPException(status_code=503, detail="Server-side speech synthesis is not configured")
    if not secret_value(settings.ELEVENLABS_API_KEY) or not settings.ELEVENLABS_VOICE_ID:
        raise HTTPException(status_code=503, detail="Voice provider is not configured")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20, read=20)) as client:
            async with client.stream(
                "POST",
                f"https://api.elevenlabs.io/v1/text-to-speech/{settings.ELEVENLABS_VOICE_ID}",
                headers={"xi-api-key": secret_value(settings.ELEVENLABS_API_KEY), "accept": "audio/mpeg", "content-type": "application/json"},
                json={"text": payload.text, "model_id": "eleven_turbo_v2_5", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
            ) as response:
                response.raise_for_status()
                chunks = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 2 * 1024 * 1024:
                        raise HTTPException(status_code=502, detail="Voice provider returned audio that was too large")
                    chunks.append(chunk)
        return Response(b"".join(chunks), media_type="audio/mpeg", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Voice provider is temporarily unavailable") from exc
