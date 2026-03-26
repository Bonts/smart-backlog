"""LLM service for AI-powered categorization, summarization, and planning."""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from ..config import OPENAI_API_KEY, OPENAI_MODEL


def get_llm() -> ChatOpenAI:
    """Get configured LLM instance."""
    return ChatOpenAI(
        model=OPENAI_MODEL,
        api_key=OPENAI_API_KEY,
        temperature=0.3,
    )


CATEGORIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a smart backlog assistant. Analyze the incoming item and suggest:
1. A category (from existing categories or suggest a new one)
2. Tags (from existing tags or suggest new ones)
3. Eisenhower quadrant (do_first / schedule / delegate / eliminate)
4. Domain (work / personal / study)
5. A brief summary (1-2 sentences)

Existing categories: {categories}
Existing tags: {tags}

Respond in JSON format:
{{
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
    ("system", """You are a task extraction assistant. Given a voice message transcription:
1. Identify actionable tasks mentioned
2. Reformulate each as a clear, concise task title
3. Extract key context for each task

Respond in JSON:
{{
    "tasks": [
        {{"title": "Clear task title", "context": "Additional context", "suggested_domain": "work"}}
    ]
}}"""),
    ("human", "Transcription:\n{transcription}"),
])
