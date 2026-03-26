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
    """Use OpenAI Vision API to extract and interpret screenshot content."""
    import base64
    from openai import OpenAI
    from ..config import OPENAI_API_KEY

    client = OpenAI(api_key=OPENAI_API_KEY)

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
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
                        "image_url": {"url": f"data:image/png;base64,{image_data}"},
                    },
                ],
            }
        ],
        max_tokens=1000,
    )
    return response.choices[0].message.content or ""


def _extract_with_tesseract(image_path: str) -> str:
    """Use Tesseract OCR for text extraction."""
    import pytesseract
    from PIL import Image

    image = Image.open(image_path)
    return pytesseract.image_to_string(image)
