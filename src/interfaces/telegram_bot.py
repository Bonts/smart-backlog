"""Smart Backlog Telegram Bot — capture and manage items on the go."""

from __future__ import annotations

import asyncio
import io
import logging
import os
import tempfile
from datetime import datetime, timedelta

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
    ItemKind,
    KanbanState,
)
from ..core.planner import generate_daily_plan
from ..core.prioritizer import get_eisenhower_matrix, matrix_to_markdown
from ..core.processor import process_input
from ..storage.database import Database
from ..storage.markdown import daily_plan_to_markdown, item_to_markdown
from ..storage.pdf_export import generate_backlog_pdf, generate_matrix_pdf

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
        "/upcoming — Items by period (1-7 days)\n"
        "/export — Export backlog as PDF\n"
        "/cleanup — Bulk archive/delete items\n"
        "/delete — Delete items\n"
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
    """List recent items in table format grouped by category."""
    items = db.list_items(limit=30)
    if not items:
        await update.message.reply_text("📭 Backlog is empty.")
        return

    q_emoji = {
        EisenhowerQuadrant.DO_FIRST: "🔴",
        EisenhowerQuadrant.SCHEDULE: "🟡",
        EisenhowerQuadrant.DELEGATE: "🟠",
        EisenhowerQuadrant.ELIMINATE: "⚪",
    }
    s_emoji = {
        KanbanState.BACKLOG: "📥",
        KanbanState.TODO: "📋",
        KanbanState.IN_PROGRESS: "🔄",
        KanbanState.DONE: "✅",
        KanbanState.ARCHIVED: "📦",
    }

    # Group by category
    grouped: dict[str, list] = {}
    for item in items:
        cat = item.ai_suggested_category or "Uncategorized"
        grouped.setdefault(cat, []).append(item)

    lines = ["📋 *Items* (" + str(len(items)) + ")\n"]
    for cat, cat_items in grouped.items():
        lines.append(f"━━━ *{cat}* ━━━")
        for item in cat_items:
            prio = q_emoji.get(item.quadrant, "❓") if item.quadrant else "❓"
            state = s_emoji.get(item.kanban_state, "")
            due = ""
            if item.deadline:
                due = f" 📅{item.deadline.strftime('%d.%m')}"
            title = item.title[:40]
            lines.append(f"{prio} {state} {title}{due}")
        lines.append("")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n... (truncated)"
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show items with toggle selection for batch delete."""
    items = db.list_items(limit=30)
    if not items:
        await update.message.reply_text("📭 Backlog is empty.")
        return

    context.user_data["select_delete"] = set()
    context.user_data["delete_items"] = [i.id for i in items]

    keyboard = _build_select_delete_keyboard(items, set())
    await update.message.reply_text(
        f"🗑 *Select items to delete* ({len(items)})\nTap to toggle ☐/☑, then press Delete Selected.",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def cmd_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bulk cleanup: archive/delete done items or purge all."""
    counts = db.count_items_by_state()
    total = sum(counts.values())
    done = counts.get("done", 0)
    archived = counts.get("archived", 0)

    text = (
        f"🧹 *Cleanup*\n\n"
        f"Total items: {total}\n"
        f"✅ Done: {done}\n"
        f"📦 Archived: {archived}\n"
    )
    keyboard = []
    if done > 0:
        keyboard.append([
            InlineKeyboardButton(f"📦 Archive done ({done})", callback_data="cleanup:archive_done"),
            InlineKeyboardButton(f"🗑 Delete done ({done})", callback_data="cleanup:delete_done"),
        ])
    if archived > 0:
        keyboard.append([
            InlineKeyboardButton(f"🗑 Delete archived ({archived})", callback_data="cleanup:delete_archived"),
        ])
    if total > 0:
        keyboard.append([
            InlineKeyboardButton(f"⚠️ Delete ALL ({total})", callback_data="cleanup:delete_all"),
        ])

    if not keyboard:
        await update.message.reply_text("📭 Nothing to clean up.")
        return

    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


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


async def cmd_upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show items for a selected period with sorting options."""
    days = 1
    sort_by = "priority"
    await update.message.reply_text(
        _format_upcoming_items(days, sort_by),
        parse_mode="Markdown",
        reply_markup=_get_upcoming_keyboard(days, sort_by),
    )


async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export backlog as PDF document."""
    keyboard = [
        [
            InlineKeyboardButton("📋 Full Backlog", callback_data="export:backlog"),
            InlineKeyboardButton("📊 Matrix", callback_data="export:matrix"),
        ],
        [
            InlineKeyboardButton("📌 Tasks only", callback_data="export:tasks"),
            InlineKeyboardButton("📝 Notes only", callback_data="export:notes"),
        ],
    ]
    await update.message.reply_text(
        "📄 Choose export format:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# --- Message Handlers ---

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages — URLs and plain text."""
    text = update.message.text.strip()

    # Handle /cancel
    if text.lower() == "/cancel":
        context.user_data.pop("editing", None)
        await update.message.reply_text("Cancelled.")
        return

    # Handle edit mode — user is sending new title
    editing_id = context.user_data.pop("editing", None)
    if editing_id:
        item = db.get_item(editing_id)
        if item:
            item.title = text
            db.update_item(item)
            keyboard = _get_item_actions_keyboard(item.id)
            await update.message.reply_text(
                _format_item_confirmation(item),
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
        else:
            await update.message.reply_text("❌ Item not found.")
        return

    status_msg = await update.message.reply_text("⏳ Processing...")

    try:
        items = await process_input(text=text, db=db)
        await status_msg.delete()
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
        context.user_data["retry"] = {"type": "text", "text": text}
        keyboard = [[InlineKeyboardButton("🔄 Retry", callback_data="retry")]]
        await update.message.reply_text(
            f"❌ Error: {e}",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages — transcribe and extract tasks."""
    status_msg = await update.message.reply_text("🎤 Transcribing voice message...")

    try:
        voice = await update.message.voice.get_file()
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            await voice.download_to_drive(f.name)
            temp_path = f.name

        items = await process_input(audio_path=temp_path, db=db)
        os.unlink(temp_path)
        await status_msg.delete()

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
        # Keep temp file for retry
        context.user_data["retry"] = {"type": "voice", "path": temp_path}
        keyboard = [[InlineKeyboardButton("🔄 Retry", callback_data="retry")]]
        await update.message.reply_text(
            f"❌ Error processing voice: {e}",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages — OCR and interpret."""
    status_msg = await update.message.reply_text("📸 Analyzing screenshot...")

    try:
        photo = await update.message.photo[-1].get_file()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            await photo.download_to_drive(f.name)
            temp_path = f.name

        items = await process_input(image_path=temp_path, db=db)
        os.unlink(temp_path)
        await status_msg.delete()

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
        # Keep temp file for retry
        context.user_data["retry"] = {"type": "photo", "path": temp_path}
        keyboard = [[InlineKeyboardButton("🔄 Retry", callback_data="retry")]]
        await update.message.reply_text(
            f"❌ Error processing screenshot: {e}",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


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
                _format_item_confirmation(item),
                parse_mode="Markdown",
                reply_markup=_get_item_actions_keyboard(item_id),
            )

    elif data.startswith("quadrant:"):
        parts = data.split(":")
        item_id, quadrant = parts[1], parts[2]
        item = db.get_item(item_id)
        if item:
            item.quadrant = EisenhowerQuadrant(quadrant)
            db.update_item(item)
            await query.edit_message_text(
                _format_item_confirmation(item),
                parse_mode="Markdown",
                reply_markup=_get_item_actions_keyboard(item_id),
            )

    elif data.startswith("state:"):
        parts = data.split(":")
        item_id, state = parts[1], parts[2]
        item = db.get_item(item_id)
        if item:
            item.kanban_state = KanbanState(state)
            db.update_item(item)
            await query.edit_message_text(
                _format_item_confirmation(item),
                parse_mode="Markdown",
                reply_markup=_get_item_actions_keyboard(item_id),
            )

    elif data.startswith("kind:"):
        parts = data.split(":")
        item_id, kind = parts[1], parts[2]
        item = db.get_item(item_id)
        if item:
            item.kind = ItemKind(kind)
            db.update_item(item)
            await query.edit_message_text(
                _format_item_confirmation(item),
                parse_mode="Markdown",
                reply_markup=_get_item_actions_keyboard(item_id),
            )

    elif data.startswith("setkind:"):
        item_id = data.split(":")[1]
        keyboard = [
            [
                InlineKeyboardButton("📌 Task", callback_data=f"kind:{item_id}:task"),
                InlineKeyboardButton("📝 Note", callback_data=f"kind:{item_id}:note"),
                InlineKeyboardButton("💡 Idea", callback_data=f"kind:{item_id}:idea"),
            ]
        ]
        await query.edit_message_text(
            "Choose kind:", reply_markup=InlineKeyboardMarkup(keyboard),
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

    elif data.startswith("delete:"):
        item_id = data.split(":")[1]
        item = db.get_item(item_id)
        title = item.title if item else "item"
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, delete", callback_data=f"confirm_delete:{item_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_delete:{item_id}"),
            ]
        ]
        await query.edit_message_text(
            f"🗑 Delete *{title}*?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data.startswith("confirm_delete:"):
        item_id = data.split(":")[1]
        item = db.get_item(item_id)
        title = item.title if item else "item"
        db.delete_item(item_id)
        await query.edit_message_text(f"🗑 *{title}* deleted.", parse_mode="Markdown")

    elif data.startswith("cancel_delete:"):
        item_id = data.split(":")[1]
        item = db.get_item(item_id)
        if item:
            await query.edit_message_text(
                _format_item_confirmation(item),
                parse_mode="Markdown",
                reply_markup=_get_item_actions_keyboard(item_id),
            )
        else:
            await query.edit_message_text("Cancelled.")

    elif data.startswith("edit:"):
        item_id = data.split(":")[1]
        context.user_data["editing"] = item_id
        item = db.get_item(item_id)
        title = item.title if item else ""
        await query.edit_message_text(
            f"✏️ Send new title for:\n_{title}_\n\nOr /cancel",
            parse_mode="Markdown",
        )

    elif data.startswith("setdue:"):
        item_id = data.split(":")[1]
        today = datetime.now()
        keyboard = [
            [
                InlineKeyboardButton("Today", callback_data=f"due:{item_id}:0"),
                InlineKeyboardButton("Tomorrow", callback_data=f"due:{item_id}:1"),
                InlineKeyboardButton("+3d", callback_data=f"due:{item_id}:3"),
            ],
            [
                InlineKeyboardButton("+1w", callback_data=f"due:{item_id}:7"),
                InlineKeyboardButton("+2w", callback_data=f"due:{item_id}:14"),
                InlineKeyboardButton("+1m", callback_data=f"due:{item_id}:30"),
            ],
            [
                InlineKeyboardButton("❌ No due date", callback_data=f"due:{item_id}:none"),
            ],
        ]
        await query.edit_message_text(
            "📅 Set due date:", reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data.startswith("due:"):
        parts = data.split(":")
        item_id, offset = parts[1], parts[2]
        item = db.get_item(item_id)
        if item:
            if offset == "none":
                item.deadline = None
            else:
                item.deadline = datetime.now() + timedelta(days=int(offset))
            db.update_item(item)
            await query.edit_message_text(
                _format_item_confirmation(item),
                parse_mode="Markdown",
                reply_markup=_get_item_actions_keyboard(item_id),
            )

    elif data == "retry":
        retry_info = context.user_data.get("retry")
        if not retry_info:
            await query.edit_message_text("Nothing to retry.")
            return
        await query.edit_message_text("🔄 Retrying...")
        try:
            if retry_info["type"] == "text":
                items = await process_input(text=retry_info["text"], db=db)
            elif retry_info["type"] == "voice":
                items = await process_input(audio_path=retry_info["path"], db=db)
            elif retry_info["type"] == "photo":
                items = await process_input(image_path=retry_info["path"], db=db)
            else:
                items = []
            for item in items:
                db.add_item(item)
                response = _format_item_confirmation(item)
                keyboard = _get_item_actions_keyboard(item.id)
                await query.message.reply_text(
                    response,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )
            # Clean up temp files on success
            if retry_info["type"] in ("voice", "photo"):
                try:
                    os.unlink(retry_info["path"])
                except (FileNotFoundError, OSError):
                    pass
            context.user_data.pop("retry", None)
        except Exception as e:
            logger.error(f"Retry failed: {e}")
            keyboard = [[InlineKeyboardButton("🔄 Retry", callback_data="retry")]]
            await query.edit_message_text(
                f"❌ Retry failed: {e}",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    elif data.startswith("upcoming:"):
        parts = data.split(":")
        days = int(parts[1])
        sort_by = parts[2] if len(parts) > 2 else "date"
        await query.edit_message_text(
            _format_upcoming_items(days, sort_by),
            parse_mode="Markdown",
            reply_markup=_get_upcoming_keyboard(days, sort_by),
        )

    elif data.startswith("export:"):
        export_type = data.split(":")[1]
        await query.edit_message_text("⏳ Generating PDF...")
        try:
            if export_type == "matrix":
                items = db.list_items(limit=200)
                pdf_bytes = generate_matrix_pdf(items)
                filename = "eisenhower_matrix.pdf"
                caption = "📊 Eisenhower Matrix"
            else:
                if export_type == "tasks":
                    all_items = db.list_items(limit=200)
                    items = [i for i in all_items if i.kind.value == "task"]
                    title = "Tasks"
                elif export_type == "notes":
                    all_items = db.list_items(limit=200)
                    items = [i for i in all_items if i.kind.value in ("note", "idea")]
                    title = "Notes & Ideas"
                else:
                    items = db.list_items(limit=200)
                    title = "Smart Backlog"
                pdf_bytes = generate_backlog_pdf(items, title)
                filename = f"{title.lower().replace(' ', '_')}.pdf"
                caption = f"📄 {title} ({len(items)} items)"

            await query.message.reply_document(
                document=io.BytesIO(pdf_bytes),
                filename=filename,
                caption=caption,
            )
            await query.edit_message_text(f"✅ {caption} — exported!")
        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            await query.edit_message_text(f"❌ Export failed: {e}")

    elif data.startswith("cleanup:"):
        action = data.split(":")[1]
        if action == "archive_done":
            count = db.archive_done_items()
            await query.edit_message_text(f"📦 Archived {count} done items.")
        elif action == "delete_done":
            count = db.delete_items_by_state("done")
            await query.edit_message_text(f"🗑 Deleted {count} done items.")
        elif action == "delete_archived":
            count = db.delete_items_by_state("archived")
            await query.edit_message_text(f"🗑 Deleted {count} archived items.")
        elif action == "delete_all":
            keyboard = [[
                InlineKeyboardButton("⚠️ YES, DELETE ALL", callback_data="cleanup:confirm_all"),
                InlineKeyboardButton("❌ Cancel", callback_data="cleanup:cancel"),
            ]]
            await query.edit_message_text(
                "⚠️ *Are you sure?* This will delete ALL items permanently!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        elif action == "confirm_all":
            count = db.delete_all_items()
            await query.edit_message_text(f"🗑 Deleted ALL {count} items.")
        elif action == "cancel":
            await query.edit_message_text("Cancelled.")

    elif data.startswith("sel:"):
        # Toggle item selection for batch delete
        item_id = data.split(":")[1]
        selected = context.user_data.get("select_delete", set())
        if item_id in selected:
            selected.discard(item_id)
        else:
            selected.add(item_id)
        context.user_data["select_delete"] = selected

        item_ids = context.user_data.get("delete_items", [])
        items = [db.get_item(iid) for iid in item_ids]
        items = [i for i in items if i is not None]
        keyboard = _build_select_delete_keyboard(items, selected)
        count = len(selected)
        await query.edit_message_text(
            f"🗑 *Select items to delete* ({len(items)})\n"
            f"Selected: {count}\nTap to toggle ☐/☑, then press Delete Selected.",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    elif data == "sel_delete_go":
        selected = context.user_data.get("select_delete", set())
        if not selected:
            await query.answer("Nothing selected!")
            return
        keyboard = [[
            InlineKeyboardButton(f"⚠️ DELETE {len(selected)} items", callback_data="sel_delete_confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="sel_delete_cancel"),
        ]]
        await query.edit_message_text(
            f"⚠️ Delete *{len(selected)}* selected items?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data == "sel_delete_confirm":
        selected = context.user_data.pop("select_delete", set())
        context.user_data.pop("delete_items", None)
        count = 0
        for item_id in selected:
            if db.delete_item(item_id):
                count += 1
        await query.edit_message_text(f"🗑 Deleted {count} items.")

    elif data == "sel_delete_cancel":
        context.user_data.pop("select_delete", None)
        context.user_data.pop("delete_items", None)
        await query.edit_message_text("Cancelled.")

    elif data == "sel_all":
        item_ids = context.user_data.get("delete_items", [])
        context.user_data["select_delete"] = set(item_ids)
        items = [db.get_item(iid) for iid in item_ids]
        items = [i for i in items if i is not None]
        keyboard = _build_select_delete_keyboard(items, set(item_ids))
        await query.edit_message_text(
            f"🗑 *Select items to delete* ({len(items)})\n"
            f"Selected: {len(items)}\nTap to toggle ☐/☑, then press Delete Selected.",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    elif data == "sel_none":
        context.user_data["select_delete"] = set()
        item_ids = context.user_data.get("delete_items", [])
        items = [db.get_item(iid) for iid in item_ids]
        items = [i for i in items if i is not None]
        keyboard = _build_select_delete_keyboard(items, set())
        await query.edit_message_text(
            f"🗑 *Select items to delete* ({len(items)})\n"
            f"Selected: 0\nTap to toggle ☐/☑, then press Delete Selected.",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )


# --- Helpers ---

def _build_select_delete_keyboard(items: list[Item], selected: set) -> InlineKeyboardMarkup:
    """Build inline keyboard with toggleable item selection for batch delete."""
    kind_emoji = {"task": "📌", "note": "📝", "idea": "💡"}
    s_emoji = {"backlog": "📥", "todo": "📋", "in_progress": "🔄", "done": "✅", "archived": "📦"}

    rows = []
    for item in items:
        check = "☑" if item.id in selected else "☐"
        ke = kind_emoji.get(item.kind.value, "")
        se = s_emoji.get(item.kanban_state.value, "")
        label = f"{check} {ke}{se} {item.title[:35]}"
        rows.append([InlineKeyboardButton(label, callback_data=f"sel:{item.id}")])

    # Action row
    count = len(selected)
    rows.append([
        InlineKeyboardButton("Select All", callback_data="sel_all"),
        InlineKeyboardButton("Deselect All", callback_data="sel_none"),
    ])
    rows.append([
        InlineKeyboardButton(f"🗑 Delete Selected ({count})", callback_data="sel_delete_go"),
    ])
    return InlineKeyboardMarkup(rows)


def _format_item_confirmation(item: Item) -> str:
    """Format item as a Telegram-friendly confirmation message."""
    kind_labels = {"task": "📌 Task", "note": "📝 Note", "idea": "💡 Idea"}
    kind_label = kind_labels.get(item.kind.value, "📌 Task")
    lines = [f"{kind_label} — *{item.title}*"]
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
    state_labels = {
        "backlog": "📥 Backlog",
        "todo": "📋 To Do",
        "in_progress": "🔄 In Progress",
        "done": "✅ Done",
        "archived": "📦 Archived",
    }
    lines.append(f"Status: {state_labels.get(item.kanban_state.value, item.kanban_state.value)}")
    if item.deadline:
        lines.append(f"📅 Due: {item.deadline.strftime('%d.%m.%Y')}")
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
        ],
        [
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit:{item_id}"),
            InlineKeyboardButton("📅 Due", callback_data=f"setdue:{item_id}"),
            InlineKeyboardButton("� Kind", callback_data=f"setkind:{item_id}"),
        ],
        [
            InlineKeyboardButton("�🗑 Delete", callback_data=f"delete:{item_id}"),
        ],
    ])


def _get_upcoming_keyboard(active_days: int, active_sort: str) -> InlineKeyboardMarkup:
    """Create keyboard for period selection and sorting."""
    day_options = [1, 2, 3, 7]
    day_buttons = []
    for d in day_options:
        label = "Today" if d == 1 else f"{d}d" if d < 7 else "Week"
        if d == active_days:
            label = f"• {label} •"
        day_buttons.append(InlineKeyboardButton(label, callback_data=f"upcoming:{d}:{active_sort}"))

    sort_buttons = []
    for s, label in [("priority", "⚡ Prio"), ("date", "📅 Date"), ("domain", "🏷 Domain")]:
        lbl = f"• {label} •" if s == active_sort else label
        sort_buttons.append(InlineKeyboardButton(lbl, callback_data=f"upcoming:{active_days}:{s}"))

    return InlineKeyboardMarkup([day_buttons, sort_buttons])


def _format_upcoming_items(days: int, sort_by: str) -> str:
    """Format items list filtered by period with sorting."""
    cutoff = datetime.now() - timedelta(days=days)
    items = db.list_items(limit=100)
    active = [
        i for i in items
        if i.kanban_state not in (KanbanState.DONE, KanbanState.ARCHIVED)
        and i.created_at >= cutoff
    ]

    quadrant_order = {
        EisenhowerQuadrant.DO_FIRST: 0,
        EisenhowerQuadrant.SCHEDULE: 1,
        EisenhowerQuadrant.DELEGATE: 2,
        EisenhowerQuadrant.ELIMINATE: 3,
    }
    if sort_by == "priority":
        active.sort(key=lambda i: quadrant_order.get(i.quadrant, 99))
    elif sort_by == "date":
        active.sort(key=lambda i: i.created_at, reverse=True)
    elif sort_by == "domain":
        active.sort(key=lambda i: (i.domain.value if i.domain else "zzz", i.created_at))

    period_label = "Today" if days == 1 else f"Last {days} days" if days < 7 else "This week"
    lines = [f"📅 *{period_label}* — {len(active)} items\n"]

    if not active:
        lines.append("_No active items for this period._")
        return "\n".join(lines)

    q_emoji = {
        EisenhowerQuadrant.DO_FIRST: "🔴",
        EisenhowerQuadrant.SCHEDULE: "🟡",
        EisenhowerQuadrant.DELEGATE: "🟠",
        EisenhowerQuadrant.ELIMINATE: "⚪",
    }
    s_emoji = {
        KanbanState.BACKLOG: "📥",
        KanbanState.TODO: "📋",
        KanbanState.IN_PROGRESS: "🔄",
    }

    for i, item in enumerate(active, 1):
        prio = q_emoji.get(item.quadrant, "❓")
        state = s_emoji.get(item.kanban_state, "")
        domain = f" `{item.domain.value}`" if item.domain else ""
        time_str = item.created_at.strftime("%H:%M")
        lines.append(f"{i}. {prio} {state} *{item.title}*{domain}  _{time_str}_")

    return "\n".join(lines)


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

    # Register command menu in Telegram
    async def post_init(application):
        await application.bot.set_my_commands([
            ("plan", "Today's daily plan"),
            ("matrix", "Eisenhower priority matrix"),
            ("board", "View kanban board"),
            ("list", "List recent items"),
            ("upcoming", "Upcoming items by period"),
            ("export", "Export backlog as PDF"),
            ("cleanup", "Bulk archive/delete items"),
            ("delete", "Delete an item by ID"),
            ("help", "Show this help"),
        ])

    app.post_init = post_init

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("plan", cmd_plan))
    app.add_handler(CommandHandler("matrix", cmd_matrix))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("delete", cmd_delete))
    app.add_handler(CommandHandler("cleanup", cmd_cleanup))
    app.add_handler(CommandHandler("upcoming", cmd_upcoming))
    app.add_handler(CommandHandler("export", cmd_export))
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
