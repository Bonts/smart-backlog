"""Quick smoke test — initialize DB, add items, verify schema."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.database import Database
from src.core.models import Item, ItemType, Domain, EisenhowerQuadrant, KanbanState, Board, Category

def main():
    db = Database(db_path="data/test_smart_backlog.db")
    db.init_db()
    print("[OK] Database initialized")

    # Check system tags
    tags = db.list_tags()
    print(f"[OK] System tags: {[t.name for t in tags]}")
    assert len(tags) >= 4, f"Expected 4+ system tags, got {len(tags)}"

    # Add an item
    item = Item(
        title="Learn Kubernetes basics",
        content="Watch intro video, read docs, set up minikube",
        item_type=ItemType.NOTE,
        domain=Domain.STUDY,
        quadrant=EisenhowerQuadrant.SCHEDULE,
        kanban_state=KanbanState.TODO,
    )
    db.add_item(item)
    print(f"[OK] Item added: {item.id}")

    # Retrieve item
    retrieved = db.get_item(item.id)
    assert retrieved is not None
    assert retrieved.title == "Learn Kubernetes basics"
    print(f"[OK] Item retrieved: {retrieved.title}")

    # Add URL item
    url_item = Item(
        title="FastAPI Documentation",
        url="https://fastapi.tiangolo.com",
        item_type=ItemType.URL,
        domain=Domain.WORK,
        quadrant=EisenhowerQuadrant.DO_FIRST,
        kanban_state=KanbanState.BACKLOG,
    )
    db.add_item(url_item)
    print(f"[OK] URL item added: {url_item.title}")

    # Add category
    cat = Category(name="DevOps", description="Infrastructure & deployment")
    db.add_category(cat)
    categories = db.list_categories()
    print(f"[OK] Categories: {[c.name for c in categories]}")

    # Add board
    board = Board(
        name="Study & Tasks",
        tag_filters=["изучить", "сделать"],
        states=[KanbanState.TODO, KanbanState.IN_PROGRESS, KanbanState.DONE],
    )
    db.add_board(board)
    boards = db.list_boards()
    print(f"[OK] Boards: {[b.name for b in boards]}")

    # List items with filters
    study_items = db.list_items(domain="study")
    assert len(study_items) == 1
    print(f"[OK] Study items: {len(study_items)}")

    work_items = db.list_items(domain="work")
    assert len(work_items) == 1
    print(f"[OK] Work items: {len(work_items)}")

    urgent_items = db.list_items(quadrant="do_first")
    assert len(urgent_items) == 1
    print(f"[OK] Urgent items: {len(urgent_items)}")

    # Update item
    item.kanban_state = KanbanState.IN_PROGRESS
    db.update_item(item)
    updated = db.get_item(item.id)
    assert updated.kanban_state == KanbanState.IN_PROGRESS
    print(f"[OK] Item updated to IN_PROGRESS")

    # Delete item
    db.delete_item(url_item.id)
    deleted = db.get_item(url_item.id)
    assert deleted is None
    print(f"[OK] Item deleted")

    # Cleanup test DB
    import gc
    gc.collect()
    try:
        os.remove("data/test_smart_backlog.db")
    except PermissionError:
        pass  # Windows file locking — will be cleaned up next run
    print("\n=== ALL TESTS PASSED ===")


if __name__ == "__main__":
    main()
