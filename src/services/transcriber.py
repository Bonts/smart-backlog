"""Voice message transcription service."""

from __future__ import annotations


async def transcribe_audio(file_path: str) -> str:
    """Transcribe audio file to text."""
    from ..config import (
        TRANSCRIPTION_PROVIDER,
        OPENAI_API_KEY,
        AZURE_OPENAI_API_KEY,
        GROQ_API_KEY,
        GEMINI_API_KEY,
    )

    if TRANSCRIPTION_PROVIDER == "gemini" and GEMINI_API_KEY:
        return await _transcribe_via_gemini(file_path)
    elif TRANSCRIPTION_PROVIDER == "groq" and GROQ_API_KEY:
        return await _transcribe_via_groq(file_path)
    elif TRANSCRIPTION_PROVIDER == "azure" and AZURE_OPENAI_API_KEY:
        return await _transcribe_via_chat(file_path)
    else:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
        return transcription.text


async def _transcribe_via_gemini(file_path: str) -> str:
    """Transcribe audio using Gemini's multimodal API."""
    import logging
    import subprocess
    import tempfile
    import os
    import google.generativeai as genai
    from ..config import GEMINI_API_KEY, GEMINI_MODEL

    logger = logging.getLogger(__name__)
    genai.configure(api_key=GEMINI_API_KEY)

    # Convert OGG to WAV if needed
    wav_path = None
    ext = file_path.rsplit(".", 1)[-1].lower()
    if ext in ("ogg", "oga", "opus"):
        wav_path = tempfile.mktemp(suffix=".wav")
        logger.info(f"Converting {ext} to WAV via ffmpeg...")
        subprocess.run(
            ["ffmpeg", "-y", "-i", file_path, "-ar", "16000", "-ac", "1", wav_path],
            capture_output=True, check=True,
        )
        audio_file = wav_path
    else:
        audio_file = file_path

    try:
        uploaded = genai.upload_file(audio_file)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            [uploaded, "Transcribe this audio exactly as spoken. Return ONLY the transcription text."],
        )
        text = response.text or ""
        logger.info(f"Gemini transcription: {text[:200]}")
        return text
    finally:
        if wav_path:
            try:
                os.unlink(wav_path)
            except OSError:
                pass


async def _transcribe_via_groq(file_path: str) -> str:
    """Transcribe audio using Groq's Whisper API."""
    import logging
    import subprocess
    import tempfile
    import os
    from groq import Groq
    from ..config import GROQ_API_KEY

    logger = logging.getLogger(__name__)
    client = Groq(api_key=GROQ_API_KEY)

    # Convert OGG to WAV if needed (Groq accepts many formats but WAV is safest)
    wav_path = None
    ext = file_path.rsplit(".", 1)[-1].lower()
    if ext in ("ogg", "oga", "opus"):
        wav_path = tempfile.mktemp(suffix=".wav")
        logger.info(f"Converting {ext} to WAV via ffmpeg...")
        subprocess.run(
            ["ffmpeg", "-y", "-i", file_path, "-ar", "16000", "-ac", "1", wav_path],
            capture_output=True, check=True,
        )
        audio_file = wav_path
    else:
        audio_file = file_path

    try:
        with open(audio_file, "rb") as f:
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=f,
            )
        logger.info(f"Groq transcription: {transcription.text[:200]}")
        return transcription.text
    finally:
        if wav_path:
            try:
                os.unlink(wav_path)
            except OSError:
                pass


async def _transcribe_via_chat(file_path: str) -> str:
    """Transcribe audio using gpt-audio model via chat completions API."""
    import base64
    import logging
    import subprocess
    import tempfile
    import os
    from openai import AzureOpenAI
    from ..config import (
        AZURE_OPENAI_API_KEY,
        AZURE_OPENAI_ENDPOINT,
        AZURE_OPENAI_API_VERSION,
    )

    logger = logging.getLogger(__name__)

    client = AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=AZURE_OPENAI_API_VERSION,
    )

    # Convert to WAV via ffmpeg (Telegram sends OGG/Opus which the API doesn't accept raw)
    wav_path = None
    ext = file_path.rsplit(".", 1)[-1].lower()
    if ext in ("ogg", "oga", "opus"):
        wav_path = tempfile.mktemp(suffix=".wav")
        src_size = os.path.getsize(file_path)
        logger.info(f"Converting {ext} ({src_size} bytes) to WAV via ffmpeg...")
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", file_path, "-ar", "16000", "-ac", "1", wav_path],
            capture_output=True, check=True,
        )
        wav_size = os.path.getsize(wav_path)
        logger.info(f"WAV conversion done: {wav_size} bytes")
        audio_file = wav_path
        audio_format = "wav"
    else:
        audio_file = file_path
        fmt_map = {"mp3": "mp3", "wav": "wav", "m4a": "mp4", "flac": "flac"}
        audio_format = fmt_map.get(ext, "wav")

    try:
        with open(audio_file, "rb") as f:
            raw_bytes = f.read()
        audio_data = base64.b64encode(raw_bytes).decode("utf-8")
        logger.info(f"Sending {len(raw_bytes)} bytes ({len(audio_data)} base64 chars) as {audio_format}")

        response = client.chat.completions.create(
            model="gpt-audio-mini-2025-10-06",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {"data": audio_data, "format": audio_format},
                        },
                        {
                            "type": "text",
                            "text": "Transcribe this audio exactly as spoken. Return ONLY the transcription text.",
                        },
                    ],
                }
            ],
            max_tokens=2000,
            timeout=60,
        )

        msg = response.choices[0].message
        logger.info(f"Response content: {repr(msg.content)}")
        logger.info(f"Response audio: {repr(getattr(msg, 'audio', None))}")
        logger.info(f"Response refusal: {repr(getattr(msg, 'refusal', None))}")
        logger.info(f"Finish reason: {response.choices[0].finish_reason}")

        # Try content first, then audio transcript
        text = msg.content
        if not text and hasattr(msg, 'audio') and msg.audio:
            text = getattr(msg.audio, 'transcript', '') or ''
            logger.info(f"Got transcript from audio field: {repr(text[:200])}")

        return text or ""
    finally:
        if wav_path:
            try:
                os.unlink(wav_path)
            except OSError:
                pass
