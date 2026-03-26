"""Configuration for Smart Backlog."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "smart_backlog.db"))

# LLM
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Transcription
TRANSCRIPTION_ENGINE = os.getenv("TRANSCRIPTION_ENGINE", "whisper")

# OCR
OCR_ENGINE = os.getenv("OCR_ENGINE", "vision")
