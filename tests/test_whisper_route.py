"""Test whisper transcription routes on Azure OpenAI."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from src.config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION

headers = {"api-key": AZURE_OPENAI_API_KEY}

# Test 1: deployment-based route
url1 = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/whisper-001/audio/transcriptions"
r1 = httpx.post(url1, headers=headers, params={"api-version": AZURE_OPENAI_API_VERSION}, timeout=10)
print(f"whisper-001 deployment: {r1.status_code} {r1.text[:200]}")

# Test 2: no deployment (model in body)
url2 = f"{AZURE_OPENAI_ENDPOINT}/openai/audio/transcriptions"
r2 = httpx.post(url2, headers=headers, params={"api-version": AZURE_OPENAI_API_VERSION},
                data={"model": "whisper-001"}, timeout=10)
print(f"direct audio: {r2.status_code} {r2.text[:200]}")

# Test 3: OpenAI-compatible route
url3 = f"{AZURE_OPENAI_ENDPOINT}/v1/audio/transcriptions"
r3 = httpx.post(url3, headers={"api-key": AZURE_OPENAI_API_KEY},
                data={"model": "whisper-001"}, timeout=10)
print(f"v1 route api-key: {r3.status_code} {r3.text[:300]}")

# Test 4: OpenAI-compatible with Bearer
url4 = f"{AZURE_OPENAI_ENDPOINT}/v1/audio/transcriptions"
r4 = httpx.post(url4, headers={"Authorization": f"Bearer {AZURE_OPENAI_API_KEY}"},
                data={"model": "whisper-1"}, timeout=10)
print(f"v1 Bearer whisper-1: {r4.status_code} {r4.text[:300]}")
