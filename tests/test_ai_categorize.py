"""Test AI categorization with Azure OpenAI."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.database import Database
from src.core.models import Item, ItemType
from src.core.categorizer import categorize_item
from src.config import LLM_PROVIDER, AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT


async def main():
    print(f"LLM Provider: {LLM_PROVIDER}")
    print(f"Azure Key: {'set' if AZURE_OPENAI_API_KEY else 'NOT SET'}")
    print(f"Azure Endpoint: {AZURE_OPENAI_ENDPOINT}")

    db = Database(db_path="data/test_ai.db")
    db.init_db()

    item = Item(
        title="Learn Kubernetes basics",
        content="Need to set up minikube, learn pods, services, deployments. For the new microservices project at work.",
        item_type=ItemType.NOTE,
    )

    print(f"\nInput: {item.title}")
    print(f"Content: {item.content}")
    print("\nCategorizing with AI...")

    result = await categorize_item(item, db)

    print(f"\n--- AI Results ---")
    print(f"Domain: {result.domain}")
    print(f"Quadrant: {result.quadrant}")
    print(f"Summary: {result.ai_summary}")
    print(f"Suggested category: {result.ai_suggested_category}")
    print(f"Suggested tags: {result.ai_suggested_tags}")

    # Cleanup
    import gc
    gc.collect()
    try:
        os.remove("data/test_ai.db")
    except (PermissionError, FileNotFoundError):
        pass

    print("\n=== AI CATEGORIZATION TEST PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())
