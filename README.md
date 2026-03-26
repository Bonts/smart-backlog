# Smart Backlog

AI-powered knowledge hub & backlog manager with smart categorization, Eisenhower matrix prioritization, and multi-interface access.

## What it does

- **Capture anything**: URLs, screenshots (OCR), voice messages (transcription), text notes
- **AI categorization**: automatic tagging, folder routing, priority suggestion
- **Eisenhower matrix**: urgent/important prioritization + domain separation (work/personal/study)
- **Kanban boards**: flexible board configuration per task type
- **Daily planning**: auto-generated daily plans with reminders
- **Learning support**: auto-generate study plans and find related resources

## Interfaces

| Interface | Purpose |
|---|---|
| **Telegram Bot** | Quick capture on the go — text, voice, screenshots, links |
| **MCP Tool** | Manage backlog from VS Code chat |

## Project Structure

```
smart-backlog/
├── src/
│   ├── core/                # Core domain logic
│   │   ├── models.py        # Data models (Item, Category, Board, etc.)
│   │   ├── categorizer.py   # AI categorization engine
│   │   ├── prioritizer.py   # Eisenhower matrix + priority logic
│   │   ├── planner.py       # Daily plan generator
│   │   └── processor.py     # Input processing pipeline
│   ├── storage/             # Data persistence
│   │   ├── database.py      # SQLite operations
│   │   └── markdown.py      # Markdown export for mobile viewing
│   ├── interfaces/          # User-facing interfaces
│   │   ├── telegram_bot.py  # Telegram bot
│   │   └── mcp_tool.py      # MCP server tool
│   ├── services/            # External service integrations
│   │   ├── llm.py           # LLM calls (categorization, summarization)
│   │   ├── ocr.py           # Screenshot text extraction
│   │   ├── transcriber.py   # Voice message transcription
│   │   └── web_scraper.py   # URL title/metadata extraction
│   └── config.py            # Configuration
├── tests/                   # Unit & integration tests
├── docs/                    # Documentation
│   └── issue.md             # Requirements & specifications
├── .env.example             # Environment variables template
├── requirements.txt         # Python dependencies
└── README.md
```

## Tech Stack

- **Python 3.11+**
- **SQLite** — local database
- **LangChain + LLM** — AI categorization, summarization, planning
- **python-telegram-bot** — Telegram interface
- **Whisper / Azure Speech** — voice transcription
- **Tesseract / Vision API** — OCR for screenshots

## Quick Start

```bash
# Clone
git clone https://github.com/Bonts/smart-backlog.git
cd smart-backlog

# Setup
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run Telegram bot
python -m src.interfaces.telegram_bot
```

## Status

🚧 **Phase 1** — Project setup & core architecture
