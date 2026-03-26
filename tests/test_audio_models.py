"""Test audio transcription via chat completions API on EPAM AI Proxy."""
import sys, os, base64
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import AzureOpenAI
from src.config import (
    AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION,
)

client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_API_VERSION,
)

# Create a tiny test OGG (silence) - or test with the models that support audio
# First, just test if gpt-audio models are reachable via chat completions
audio_models = [
    "gpt-audio-mini-2025-10-06",
    "gpt-audio-2025-08-28",
    "gpt-4o-mini-transcribe",
    "gpt-4o-transcribe",
]

for model in audio_models:
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=10,
        )
        print(f"{model}: OK - {r.choices[0].message.content}")
    except Exception as e:
        print(f"{model}: ERROR - {str(e)[:150]}")
