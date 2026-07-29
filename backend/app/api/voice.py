import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.api.auth import get_current_user
from app.db.models import User
from app.core.config import settings

router = APIRouter(prefix="/api/voice", tags=["Voice Assistant"])

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=400, detail="Groq API key not configured")

    audio_bytes = await file.read()
    filename = file.filename or "recording.wav"
    content_type = file.content_type or "audio/wav"

    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
    files = {"file": (filename, audio_bytes, content_type)}
    data = {"model": "whisper-large-v3"}

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
                timeout=30.0
            )
            if res.status_code == 200:
                return res.json()
            
            # Retry fallback model
            data["model"] = "distil-whisper-large-v3-en"
            res2 = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
                timeout=30.0
            )
            if res2.status_code == 200:
                return res2.json()

            raise HTTPException(status_code=res.status_code, detail=f"Voice transcription failed: {res.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice transcription error: {str(e)}")
