"""Smart Backlog Telegram Bot — capture and manage items on the go."""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ..config import TELEGRAM_BOT_TOKEN
from ..core.models import (
    Domain,
    EisenhowerQuadrant,
    Item,
    KanbanState,
)
from ..core.planner import generate_daily_plan
from ..core.prioritizer import get_eisenhower_matrix, matrix_to_markdown
from ..core.processor import process_input
from ..storage.database import Database
from ..storage.markdown import daily_plan_to_markdown, item_to_markdown

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()


# --- Command Handlers ---

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "🧠 *Smart Backlog* — AI-powered knowledge hub\n\n"
        "Send me anything:\n"
        "• 🔗 URL — save & categorize a link\n"
        "• 📝 Text — create a note/task\n"
        "• 🎤 Voice — transcribe & extract tasks\n"
        "• 📸 Photo — OCR & interpret screenshot\n\n"
        "*Commands:*\n"
        "/plan — Today's daily plan\n"
        "/matrix — Eisenhower priority matrix\n"
        "/board — View kanban board\n"
        "/list — List recent items\n"
        "/help — Show this help",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await cmd_start(update, context)


async def cmd_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and show daily plan."""
    await update.message.reply_text("⏳ Generating daily plan...")
    try:
        plan = await generate_daily_plan(db)
        items = [db.get_item(iid) for iid in plan.items]
        items = [i for i in items if i is not None]
        md = daily_plan_to_markdown(plan, items)
        await update.message.reply_text(md, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Plan generation failed: {e}")
        await update.message.reply_text(f"❌ Failed to generate plan: {e}")


async def cmd_matrix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Eisenhower priority matrix."""
    items = db.list_items(limit=100)
    active = [i for i in items if i.kanban_state != KanbanState.ARCHIVED]
    matrix = get_eisenhower_matrix(active)
    md = matrix_to_markdown(matrix)
    if len(md) > 4000:
        md = md[:4000] + "\n\n... (truncated)"
    await update.message.reply_text(md, parse_mode="Markdown")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List recent items."""
    items = db.list_items(limit=10)
    if not items:
        await update.message.reply_text("📭 Backlog is empty.")
        return
    lines = ["📋 *Recent Items:*\n"]
    for i, item in enumerate(items, 1):
        domain = f" `{item.domain.value}`" if item.domain else ""
        quadrant_emoji = {
            EisenhowerQuadrant.DO_FIRST: "🔴",
            EisenhowerQuadrant.SCHEDULE: "🟡",
            EisenhowerQuadrant.DELEGATE: "🟠",
            EisenhowerQuadrant.ELIMINATE: "⚪",
        }
        prio = quadrant_emoji.get(item.quadrant, "❓") if item.quadrant else "❓"
        state_emoji = {
            KanbanState.BACKLOG: "📥",
            KanbanState.TODO: "📋",
            KanbanState.IN_PROGRESS: "🔄",
            KanbanState.DONE: "✅",
            KanbanState.ARCHIVED: "📦",
        }
        state = state_emoji.get(item.kanban_state, "")
        lines.append(f"{i}. {prio} {state} *{item.title}*{domain}")
        if item.ai_summary:
            lines.append(f"   _{item.ai_summary}_")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show kanban board view."""
    boards = db.list_boards()
    if not boards:
        # Default: show all items grouped by state
        items = db.list_items(limit=50)
        grouped: dict[str, list] = {}
        for item in items:
            state = item.kanban_state.value
            grouped.setdefault(state, []).append(item)

        state_labels = {
            "backlog": "📥 Backlog",
            "todo": "📋 To Do",
            "in_progress": "🔄 In Progress",
            "done": "✅ Done",
        }
        lines = ["📊 *Kanban Board*\n"]
        for state, label in state_labels.items():
            state_items = grouped.get(state, [])
            lines.append(f"*{label}* ({len(state_items)})")
            for item in state_items[:5]:
                lines.append(f"  • {item.title}")
            if len(state_items) > 5:
                lines.append(f"  _... and {len(state_items) - 5} more_")
            lines.append("")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    else:
        # Show board selection
        keyboard = [
            [InlineKeyboardButton(b.name, callback_data=f"board:{b.id}")]
            for b in boards
        ]
        await update.message.reply_text(
            "Choose a board:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


# --- Message Handlers ---

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages — URLs and plain text."""
    text = update.message.text.strip()
    await update.message.reply_text("⏳ Processing...")

    try:
        items = await process_input(text=text, db=db)
        for item in items:
            db.add_item(item)
            response = _format_item_confirmation(item)
            keyboard = _get_item_actions_keyboard(item.id)
            await update.message.reply_text(
                response,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages — transcribe and extract tasks."""
    await update.message.reply_text("🎤 Transcribing voice message...")

    try:
        voice = await update.message.voice.get_file()
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            await voice.download_to_drive(f.name)
            temp_path = f.name

        items = await process_input(audio_path=temp_path, db=db)
        os.unlink(temp_path)

        for item in items:
            db.add_item(item)
            response = _format_item_confirmation(item)
            keyboard = _get_item_actions_keyboard(item.id)
            await update.message.reply_text(
                response,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
    except Exception as e:
        logger.error(f"Voice processing failed: {e}")
        await update.message.reply_text(f"❌ Error processing voice: {e}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages — OCR and interpret."""
    await update.message.reply_text("📸 Analyzing screenshot...")

    try:
        photo = await update.message.photo[-1].get_file()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            await photo.download_to_drive(f.name)
            temp_path = f.name

        items = await process_input(image_path=temp_path, db=db)
        os.unlink(temp_path)

        for item in items:
            db.add_item(item)
            response = _format_item_confirmation(item)
            keyboard = _get_item_actions_keyboard(item.id)
            await update.message.reply_text(
                response,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
    except Exception as e:
        logger.error(f"Photo processing failed: {e}")
        await update.message.reply_text(f"❌ Error processing screenshot: {e}")


# --- Callback Handlers ---

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("domain:"):
        parts = data.split(":")
        item_id, domain = parts[1], parts[2]
        item = db.get_item(item_id)
        if item:
            item.domain = Domain(domain)
            db.update_item(item)
            await query.edit_message_text(
                f"✅ Domain set to *{domain}*\n\n" + _format_item_confirmation(item),
                parse_mode="Markdown",
            )

    elif data.startswith("quadrant:"):
        parts = data.split(":")
        item_id, quadrant = parts[1], parts[2]
        item = db.get_item(item_id)
        if item:
            item.quadrant = EisenhowerQuadrant(quadrant)
            db.update_item(item)
            await query.edit_message_text(
                f"✅ Priority set to *{quadrant}*\n\n" + _format_item_confirmation(item),
                parse_mode="Markdown",
            )

    elif data.startswith("state:"):
        parts = data.split(":")
        item_id, state = parts[1], parts[2]
        item = db.get_item(item_id)
        if item:
            item.kanban_state = KanbanState(state)
            db.update_item(item)
            await query.edit_message_text(
                f"✅ Status → *{state}*\n\n" + _format_item_confirmation(item),
                parse_mode="Markdown",
            )

    elif data.startswith("setdomain:"):
        item_id = data.split(":")[1]
        keyboard = [
            [
                InlineKeyboardButton("💼 Work", callback_data=f"domain:{item_id}:work"),
                InlineKeyboardButton("🏠 Personal", callback_data=f"domain:{item_id}:personal"),
                InlineKeyboardButton("📚 Study", callback_data=f"domain:{item_id}:study"),
            ]
        ]
        await query.edit_message_text(
            "Choose domain:", reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data.startswith("setprio:"):
        item_id = data.split(":")[1]
        keyboard = [
            [
                InlineKeyboardButton("🔴 Do First", callback_data=f"quadrant:{item_id}:do_first"),
                InlineKeyboardButton("🟡 Schedule", callback_data=f"quadrant:{item_id}:schedule"),
            ],
            [
                InlineKeyboardButton("🟠 Delegate", callback_data=f"quadrant:{item_id}:delegate"),
                InlineKeyboardButton("⚪ Eliminate", callback_data=f"quadrant:{item_id}:eliminate"),
            ],
        ]
        await query.edit_message_text(
            "Choose priority:", reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data.startswith("setstate:"):
        item_id = data.split(":")[1]
        keyboard = [
            [
                InlineKeyboardButton("📋 To Do", callback_data=f"state:{item_id}:todo"),
                InlineKeyboardButton("🔄 In Progress", callback_data=f"state:{item_id}:in_progress"),
            ],
            [
                InlineKeyboardButton("✅ Done", callback_data=f"state:{item_id}:done"),
                InlineKeyboardButton("📦 Archive", callback_data=f"state:{item_id}:archived"),
            ],
        ]
        await query.edit_message_text(
            "Choose status:", reply_markup=InlineKeyboardMarkup(keyboard),
        )


# --- Helpers ---

def _format_item_confirmation(item: Item) -> str:
    """Format item as a Telegram-friendly confirmation message."""
    lines = [f"✅ *Saved:* {item.title}"]
    if item.url:
        lines.append(f"🔗 {item.url}")
    if item.domain:
        domain_emoji = {"work": "💼", "personal": "🏠", "study": "📚"}
        lines.append(f"{domain_emoji.get(item.domain.value, '')} {item.domain.value}")
    if item.quadrant:
        q_labels = {
            "do_first": "🔴 Do First",
            "schedule": "🟡 Schedule",
            "delegate": "🟠 Delegate",
            "eliminate": "⚪ Eliminate",
        }
        lines.append(f"Priority: {q_labels.get(item.quadrant.value, item.quadrant.value)}")
    if item.ai_summary:
        lines.append(f"\n_{item.ai_summary}_")
    if item.ai_suggested_tags:
        lines.append(f"Tags: {', '.join(item.ai_suggested_tags)}")
    return "\n".join(lines)


def _get_item_actions_keyboard(item_id: str) -> InlineKeyboardMarkup:
    """Create inline keyboard with quick actions for an item."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏷 Domain", callback_data=f"setdomain:{item_id}"),
            InlineKeyboardButton("⚡ Priority", callback_data=f"setprio:{item_id}"),
            InlineKeyboardButton("📊 Status", callback_data=f"setstate:{item_id}"),
        ]
    ])


# --- Main ---

def run_bot():
    """Start the Telegram bot."""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set in .env")
        print("   Get a token from @BotFather on Telegram")
        return

    db.init_db()
    print("🧠 Smart Backlog bot starting...")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("plan", cmd_plan))
    app.add_handler(CommandHandler("matrix", cmd_matrix))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("board", cmd_board))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Callbacks
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("✅ Bot is running! Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_bot()
