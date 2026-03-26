"""Voice message transcription service."""

from __future__ import annotations

# Placeholder — will integrate Whisper or Azure Speech
# For now, uses OpenAI Whisper API


async def transcribe_audio(file_path: str) -> str:
    """Transcribe audio file to text using Whisper."""
    from openai import OpenAI
    from ..config import OPENAI_API_KEY

    client = OpenAI(api_key=OPENAI_API_KEY)
    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
    return transcription.text
