"""LLM service for AI-powered categorization, summarization, and planning."""

from __future__ import annotations

from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from ..config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_DEPLOYMENT,
    AZURE_OPENAI_API_DEPLOYMENT_FAST,
)


def get_llm(profile: str = "fast") -> ChatOpenAI | AzureChatOpenAI:
    """Get configured LLM instance. Supports azure and openai providers."""
    if LLM_PROVIDER == "azure" and AZURE_OPENAI_API_KEY:
        deployment = AZURE_OPENAI_API_DEPLOYMENT_FAST or AZURE_OPENAI_API_DEPLOYMENT
        if profile == "smart":
            deployment = AZURE_OPENAI_API_DEPLOYMENT
        return AzureChatOpenAI(
            azure_deployment=deployment,
            api_version=AZURE_OPENAI_API_VERSION,
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            temperature=0.3,
            max_tokens=2000,
        )
    return ChatOpenAI(
        model=OPENAI_MODEL,
        api_key=OPENAI_API_KEY,
        temperature=0.3,
    )


CATEGORIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a smart backlog assistant. Analyze the incoming item and suggest:
1. Kind: "task" (actionable, has a clear action), "note" (information/reference to save), or "idea" (creative thought for later)
2. A category (from existing categories or suggest a new one)
3. Tags (from existing tags or suggest new ones)
4. Eisenhower quadrant (do_first / schedule / delegate / eliminate) — only for tasks
5. Domain (work / personal / study)
6. A brief summary (1-2 sentences)

Existing categories: {categories}
Existing tags: {tags}

Respond in JSON format:
{{
    "kind": "task",
    "category": "suggested category name",
    "tags": ["tag1", "tag2"],
    "quadrant": "schedule",
    "domain": "work",
    "summary": "Brief summary of the item"
}}"""),
    ("human", "Item title: {title}\nItem content: {content}\nItem type: {item_type}"),
])

DAILY_PLAN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a productivity assistant. Generate a focused daily plan from the user's backlog.
Prioritize items in this order:
1. DO FIRST (urgent + important)
2. SCHEDULE (important, not urgent)
3. Items with approaching deadlines

Keep the plan realistic — max 5-7 items per day.
Respond in JSON:
{{
    "selected_item_ids": ["id1", "id2"],
    "summary": "Today's focus: ..."
}}"""),
    ("human", "Today: {date}\nBacklog items:\n{items}"),
])

VOICE_TO_TASKS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a task extraction assistant. Given a voice message transcription (in Russian or English):
1. Identify actionable tasks mentioned
2. Reformulate each as a clear, concise task title in the SAME language as the original transcription
3. Extract key context for each task

Respond in JSON:
{{
    "tasks": [
        {{"title": "Clear task title", "context": "Additional context", "suggested_domain": "work"}}
    ]
}}"""),
    ("human", "Transcription:\n{transcription}"),
])
