"""Core data models for Smart Backlog."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --- Enums ---

class ItemType(str, Enum):
    URL = "url"
    NOTE = "note"
    VOICE = "voice"
    SCREENSHOT = "screenshot"


class EisenhowerQuadrant(str, Enum):
    DO_FIRST = "do_first"           # Urgent + Important
    SCHEDULE = "schedule"           # Not Urgent + Important
    DELEGATE = "delegate"           # Urgent + Not Important
    ELIMINATE = "eliminate"          # Not Urgent + Not Important


class Domain(str, Enum):
    WORK = "work"
    PERSONAL = "personal"
    STUDY = "study"


class KanbanState(str, Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ARCHIVED = "archived"


class ItemKind(str, Enum):
    TASK = "task"           # Actionable task
    NOTE = "note"           # Information / reference
    IDEA = "idea"           # Idea for later


# --- Models ---

class Tag(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    color: Optional[str] = None
    is_system: bool = False  # System tags: изучить, сделать, идеи, ежедневник


class Category(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    parent_id: Optional[str] = None
    description: Optional[str] = None
    auto_rules: Optional[str] = None  # JSON rules for auto-routing
    created_by_ai: bool = False


class Item(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str = ""
    raw_input: str = ""  # Original input before processing
    item_type: ItemType = ItemType.NOTE
    kind: ItemKind = ItemKind.TASK  # task / note / idea
    url: Optional[str] = None

    # Organization
    category_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)  # Tag IDs
    domain: Optional[Domain] = None

    # Priority
    quadrant: Optional[EisenhowerQuadrant] = None
    priority_score: Optional[float] = None  # 0.0 - 1.0
    deadline: Optional[datetime] = None

    # Kanban
    kanban_state: KanbanState = KanbanState.BACKLOG
    board_id: Optional[str] = None

    # AI metadata
    ai_summary: Optional[str] = None
    ai_suggested_category: Optional[str] = None
    ai_suggested_tags: list[str] = Field(default_factory=list)
    ai_suggested_quadrant: Optional[EisenhowerQuadrant] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Board(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    tag_filters: list[str] = Field(default_factory=list)  # Show items with these tags
    domain_filter: Optional[Domain] = None
    states: list[KanbanState] = Field(
        default_factory=lambda: [
            KanbanState.TODO,
            KanbanState.IN_PROGRESS,
            KanbanState.DONE,
        ]
    )


class DailyPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: str  # YYYY-MM-DD
    items: list[str] = Field(default_factory=list)  # Item IDs
    summary: str = ""
    generated_at: datetime = Field(default_factory=datetime.now)
