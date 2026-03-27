"""SQLite storage layer for Smart Backlog."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from ..config import DATABASE_PATH
from ..core.models import (
    Board,
    Category,
    DailyPlan,
    Item,
    Tag,
)

# Schema version for future migrations
SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT DEFAULT '',
    raw_input TEXT DEFAULT '',
    item_type TEXT DEFAULT 'note',
    kind TEXT DEFAULT 'task',
    url TEXT,
    category_id TEXT,
    tags TEXT DEFAULT '[]',
    domain TEXT,
    quadrant TEXT,
    priority_score REAL,
    deadline TEXT,
    kanban_state TEXT DEFAULT 'backlog',
    board_id TEXT,
    ai_summary TEXT,
    ai_suggested_category TEXT,
    ai_suggested_tags TEXT DEFAULT '[]',
    ai_suggested_quadrant TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id TEXT,
    description TEXT,
    auto_rules TEXT,
    created_by_ai INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tags (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    color TEXT,
    is_system INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS boards (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    tag_filters TEXT DEFAULT '[]',
    domain_filter TEXT,
    states TEXT DEFAULT '["todo","in_progress","done"]'
);

CREATE TABLE IF NOT EXISTS daily_plans (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    items TEXT DEFAULT '[]',
    summary TEXT DEFAULT '',
    generated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_items_category ON items(category_id);
CREATE INDEX IF NOT EXISTS idx_items_domain ON items(domain);
CREATE INDEX IF NOT EXISTS idx_items_quadrant ON items(quadrant);
CREATE INDEX IF NOT EXISTS idx_items_kanban_state ON items(kanban_state);
CREATE INDEX IF NOT EXISTS idx_items_board ON items(board_id);
CREATE INDEX IF NOT EXISTS idx_daily_plans_date ON daily_plans(date);
"""

SYSTEM_TAGS = [
    {"name": "изучить", "color": "#3498db", "is_system": True},
    {"name": "сделать", "color": "#e74c3c", "is_system": True},
    {"name": "идеи", "color": "#f39c12", "is_system": True},
    {"name": "ежедневник", "color": "#2ecc71", "is_system": True},
]


class Database:
    """SQLite database for Smart Backlog."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DATABASE_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_db(self):
        """Initialize database schema and seed system tags."""
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)
            # Migration: add kind column if missing
            cols = [r["name"] for r in conn.execute("PRAGMA table_info(items)").fetchall()]
            if "kind" not in cols:
                conn.execute("ALTER TABLE items ADD COLUMN kind TEXT DEFAULT 'task'")
            # Seed system tags
            for tag_data in SYSTEM_TAGS:
                conn.execute(
                    "INSERT OR IGNORE INTO tags (id, name, color, is_system) "
                    "VALUES (lower(hex(randomblob(16))), ?, ?, ?)",
                    (tag_data["name"], tag_data["color"], tag_data["is_system"]),
                )
            conn.commit()

    # --- Items ---

    def add_item(self, item: Item) -> Item:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO items
                   (id, title, content, raw_input, item_type, kind, url,
                    category_id, tags, domain, quadrant, priority_score,
                    deadline, kanban_state, board_id, ai_summary,
                    ai_suggested_category, ai_suggested_tags,
                    ai_suggested_quadrant, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    item.id, item.title, item.content, item.raw_input,
                    item.item_type.value, item.kind.value, item.url, item.category_id,
                    json.dumps(item.tags), item.domain.value if item.domain else None,
                    item.quadrant.value if item.quadrant else None,
                    item.priority_score, item.deadline.isoformat() if item.deadline else None,
                    item.kanban_state.value, item.board_id,
                    item.ai_summary, item.ai_suggested_category,
                    json.dumps(item.ai_suggested_tags),
                    item.ai_suggested_quadrant.value if item.ai_suggested_quadrant else None,
                    item.created_at.isoformat(), item.updated_at.isoformat(),
                ),
            )
            conn.commit()
        return item

    def get_item(self, item_id: str) -> Optional[Item]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
            if row:
                return self._row_to_item(row)
        return None

    def list_items(
        self,
        domain: Optional[str] = None,
        quadrant: Optional[str] = None,
        kanban_state: Optional[str] = None,
        board_id: Optional[str] = None,
        category_id: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50,
    ) -> list[Item]:
        query = "SELECT * FROM items WHERE 1=1"
        params: list = []
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        if quadrant:
            query += " AND quadrant = ?"
            params.append(quadrant)
        if kanban_state:
            query += " AND kanban_state = ?"
            params.append(kanban_state)
        if board_id:
            query += " AND board_id = ?"
            params.append(board_id)
        if category_id:
            query += " AND category_id = ?"
            params.append(category_id)
        if tag:
            query += " AND tags LIKE ?"
            params.append(f"%{tag}%")
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_item(r) for r in rows]

    def update_item(self, item: Item) -> Item:
        from datetime import datetime
        item.updated_at = datetime.now()
        with self._connect() as conn:
            conn.execute(
                """UPDATE items SET title=?, content=?, category_id=?, tags=?,
                   domain=?, quadrant=?, priority_score=?, deadline=?,
                   kanban_state=?, board_id=?, ai_summary=?,
                   ai_suggested_category=?, ai_suggested_tags=?,
                   ai_suggested_quadrant=?, kind=?, updated_at=?
                   WHERE id=?""",
                (
                    item.title, item.content, item.category_id,
                    json.dumps(item.tags),
                    item.domain.value if item.domain else None,
                    item.quadrant.value if item.quadrant else None,
                    item.priority_score,
                    item.deadline.isoformat() if item.deadline else None,
                    item.kanban_state.value, item.board_id,
                    item.ai_summary, item.ai_suggested_category,
                    json.dumps(item.ai_suggested_tags),
                    item.ai_suggested_quadrant.value if item.ai_suggested_quadrant else None,
                    item.kind.value, item.updated_at.isoformat(), item.id,
                ),
            )
            conn.commit()
        return item

    def delete_item(self, item_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_items_by_state(self, state: str) -> int:
        """Delete all items with given kanban_state. Returns count deleted."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM items WHERE kanban_state = ?", (state,))
            conn.commit()
            return cursor.rowcount

    def archive_done_items(self) -> int:
        """Move all done items to archived. Returns count archived."""
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE items SET kanban_state = 'archived' WHERE kanban_state = 'done'"
            )
            conn.commit()
            return cursor.rowcount

    def count_items_by_state(self) -> dict[str, int]:
        """Return counts of items per kanban_state."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT kanban_state, COUNT(*) FROM items GROUP BY kanban_state"
            ).fetchall()
            return {row[0]: row[1] for row in rows}

    def delete_all_items(self) -> int:
        """Delete ALL items. Returns count deleted."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM items")
            conn.commit()
            return cursor.rowcount

    # --- Categories ---

    def add_category(self, category: Category) -> Category:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO categories VALUES (?,?,?,?,?,?)",
                (category.id, category.name, category.parent_id,
                 category.description, category.auto_rules,
                 1 if category.created_by_ai else 0),
            )
            conn.commit()
        return category

    def list_categories(self) -> list[Category]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM categories").fetchall()
            return [
                Category(
                    id=r["id"], name=r["name"], parent_id=r["parent_id"],
                    description=r["description"], auto_rules=r["auto_rules"],
                    created_by_ai=bool(r["created_by_ai"]),
                )
                for r in rows
            ]

    # --- Tags ---

    def list_tags(self) -> list[Tag]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM tags").fetchall()
            return [
                Tag(id=r["id"], name=r["name"], color=r["color"],
                    is_system=bool(r["is_system"]))
                for r in rows
            ]

    def add_tag(self, tag: Tag) -> Tag:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tags VALUES (?,?,?,?)",
                (tag.id, tag.name, tag.color, 1 if tag.is_system else 0),
            )
            conn.commit()
        return tag

    # --- Boards ---

    def add_board(self, board: Board) -> Board:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO boards VALUES (?,?,?,?,?,?)",
                (board.id, board.name, board.description,
                 json.dumps(board.tag_filters),
                 board.domain_filter.value if board.domain_filter else None,
                 json.dumps([s.value for s in board.states])),
            )
            conn.commit()
        return board

    def list_boards(self) -> list[Board]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM boards").fetchall()
            return [
                Board(
                    id=r["id"], name=r["name"], description=r["description"],
                    tag_filters=json.loads(r["tag_filters"]),
                    domain_filter=r["domain_filter"],
                    states=json.loads(r["states"]),
                )
                for r in rows
            ]

    # --- Daily Plans ---

    def save_daily_plan(self, plan: DailyPlan) -> DailyPlan:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO daily_plans VALUES (?,?,?,?,?)",
                (plan.id, plan.date, json.dumps(plan.items),
                 plan.summary, plan.generated_at.isoformat()),
            )
            conn.commit()
        return plan

    def get_daily_plan(self, date: str) -> Optional[DailyPlan]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM daily_plans WHERE date = ?", (date,)
            ).fetchone()
            if row:
                return DailyPlan(
                    id=row["id"], date=row["date"],
                    items=json.loads(row["items"]),
                    summary=row["summary"],
                    generated_at=row["generated_at"],
                )
        return None

    # --- Helpers ---

    @staticmethod
    def _row_to_item(row) -> Item:
        return Item(
            id=row["id"], title=row["title"], content=row["content"],
            raw_input=row["raw_input"], item_type=row["item_type"],
            kind=row["kind"] or "task",
            url=row["url"], category_id=row["category_id"],
            tags=json.loads(row["tags"]), domain=row["domain"],
            quadrant=row["quadrant"], priority_score=row["priority_score"],
            deadline=row["deadline"], kanban_state=row["kanban_state"],
            board_id=row["board_id"], ai_summary=row["ai_summary"],
            ai_suggested_category=row["ai_suggested_category"],
            ai_suggested_tags=json.loads(row["ai_suggested_tags"]),
            ai_suggested_quadrant=row["ai_suggested_quadrant"],
            created_at=row["created_at"], updated_at=row["updated_at"],
        )
