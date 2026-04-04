"""OCR service for screenshot text extraction."""

from __future__ import annotations

from ..config import OCR_ENGINE

_VISION_PROMPT = """Analyze this image and respond ONLY with valid JSON (no markdown, no code fences).
Identify the content type and extract key information.

Rules:
- BOOK cover/photo: {"type": "book", "title": "Book Title", "author": "Author Name", "original_title": "Original title if translated, otherwise empty"}
- MUSIC album/vinyl/playlist: {"type": "music", "title": "Album or Song Title", "artist": "Artist Name"}
- MOVIE/TV show poster: {"type": "movie", "title": "Movie Title", "director": "Director Name", "year": "Year"}
- WEBPAGE/article screenshot: {"type": "web", "title": "Page title", "content": "key text content"}
- CODE screenshot: {"type": "code", "title": "What the code does (max 10 words)", "content": "extracted code"}
- PRESENTATION/slide: {"type": "slide", "title": "Slide title", "content": "key points"}
- CHAT/message screenshot: {"type": "chat", "title": "Topic of conversation (max 10 words)", "content": "key messages"}
- DOCUMENT/PDF: {"type": "doc", "title": "Document title", "content": "key text"}
- Otherwise: {"type": "other", "title": "Brief description (max 10 words)", "content": "what you see"}

Respond ONLY with the JSON object."""


async def extract_text_from_image(image_path: str) -> str:
    """Extract text from screenshot using configured OCR engine."""
    if OCR_ENGINE == "vision":
        return await _extract_with_vision(image_path)
    else:
        return _extract_with_tesseract(image_path)


async def _extract_with_vision(image_path: str) -> str:
    """Use Vision API to extract and interpret screenshot content."""
    import base64
    from ..config import (
        VISION_PROVIDER,
        OPENAI_API_KEY,
        AZURE_OPENAI_API_KEY,
        AZURE_OPENAI_ENDPOINT,
        AZURE_OPENAI_API_VERSION,
        AZURE_OPENAI_API_DEPLOYMENT,
        GEMINI_API_KEY,
    )

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # Detect media type from extension
    ext = image_path.rsplit(".", 1)[-1].lower()
    media_types = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp"}
    media_type = media_types.get(ext, "image/jpeg")

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": _VISION_PROMPT,
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{media_type};base64,{image_data}"},
                },
            ],
        }
    ]

    if VISION_PROVIDER == "gemini" and GEMINI_API_KEY:
        return await _extract_with_gemini(image_path)
    elif VISION_PROVIDER == "groq":
        # Groq doesn't support vision — fall back to tesseract
        return _extract_with_tesseract(image_path)
    elif VISION_PROVIDER == "azure" and AZURE_OPENAI_API_KEY:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
        )
        response = client.chat.completions.create(
            model=AZURE_OPENAI_API_DEPLOYMENT,
            messages=messages,
            max_tokens=1000,
        )
    else:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1000,
        )
    return response.choices[0].message.content or ""


async def _extract_with_gemini(image_path: str) -> str:
    """Use Gemini Vision to extract text from screenshot."""
    from google import genai
    from ..config import GEMINI_API_KEY, GEMINI_MODEL
    from PIL import Image

    client = genai.Client(api_key=GEMINI_API_KEY)
    image = Image.open(image_path)
    response = await client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=[_VISION_PROMPT, image],
    )
    return response.text or ""


def _extract_with_tesseract(image_path: str) -> str:
    """Use Tesseract OCR for text extraction."""
    import pytesseract
    from PIL import Image

    image = Image.open(image_path)
    return pytesseract.image_to_string(image, lang="eng+rus")
