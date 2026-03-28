"""Configuration for Smart Backlog."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root, override system env vars
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

# Paths
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "smart_backlog.db"))

# LLM
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")  # groq | gemini | azure | openai
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Azure OpenAI
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_DEPLOYMENT = os.getenv("AZURE_OPENAI_API_DEPLOYMENT", "")
AZURE_OPENAI_API_DEPLOYMENT_FAST = os.getenv("AZURE_OPENAI_API_DEPLOYMENT_FAST", "")

# Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_MODEL_FAST = os.getenv("GROQ_MODEL_FAST", "llama-3.1-8b-instant")

# Google Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_MODEL_FAST = os.getenv("GEMINI_MODEL_FAST", "gemini-2.0-flash-lite")

# Per-feature provider overrides (default = use LLM_PROVIDER for everything)
# Set these to use a different provider for vision/transcription than for text
VISION_PROVIDER = os.getenv("VISION_PROVIDER", "") or LLM_PROVIDER
TRANSCRIPTION_PROVIDER = os.getenv("TRANSCRIPTION_PROVIDER", "") or LLM_PROVIDER

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_TELEGRAM_USERS = [
    int(uid.strip())
    for uid in os.getenv("ALLOWED_TELEGRAM_USERS", "").split(",")
    if uid.strip().isdigit()
]

# Transcription
TRANSCRIPTION_ENGINE = os.getenv("TRANSCRIPTION_ENGINE", "whisper")

# OCR
OCR_ENGINE = os.getenv("OCR_ENGINE", "vision")
