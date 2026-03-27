"""OCR service for screenshot text extraction."""

from __future__ import annotations

from ..config import OCR_ENGINE


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
        LLM_PROVIDER,
        OPENAI_API_KEY,
        AZURE_OPENAI_API_KEY,
        AZURE_OPENAI_ENDPOINT,
        AZURE_OPENAI_API_VERSION,
        AZURE_OPENAI_API_DEPLOYMENT,
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
                    "text": "Extract all text and describe the key content from this screenshot. "
                            "Format as structured notes with bullet points.",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{media_type};base64,{image_data}"},
                },
            ],
        }
    ]

    if LLM_PROVIDER == "azure" and AZURE_OPENAI_API_KEY:
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


def _extract_with_tesseract(image_path: str) -> str:
    """Use Tesseract OCR for text extraction."""
    import pytesseract
    from PIL import Image

    image = Image.open(image_path)
    return pytesseract.image_to_string(image)
