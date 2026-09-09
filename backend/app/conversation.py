"""Conversation manager: persistence and history assembly.

Sits between the API routes and the database. Owns all CRUD for conversations
and messages, and builds the message payload sent to the LLM.
"""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .config import get_settings
from .logging_config import get_logger
from .models import Conversation, Message

logger = get_logger(__name__)

# Keep the most recent N messages when building LLM context to bound token use.
MAX_HISTORY_MESSAGES = 40


class ConversationManager:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    # --- Conversations ------------------------------------------------------
    async def list_conversations(self) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation).order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())

    async def create_conversation(
        self,
        *,
        title: str | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
    ) -> Conversation:
        conversation = Conversation(
            title=title or "New conversation",
            system_prompt=system_prompt
            if system_prompt is not None
            else self.settings.default_system_prompt,
            temperature=temperature
            if temperature is not None
            else self.settings.default_temperature,
        )
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        logger.info("Created conversation %s", conversation.id)
        return conversation

    async def get_conversation(
        self, conversation_id: str, *, with_messages: bool = False
    ) -> Conversation | None:
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        if with_messages:
            stmt = stmt.options(selectinload(Conversation.messages))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_conversation(
        self,
        conversation: Conversation,
        *,
        title: str | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
    ) -> Conversation:
        if title is not None:
            conversation.title = title
        if system_prompt is not None:
            conversation.system_prompt = system_prompt
        if temperature is not None:
            conversation.temperature = temperature
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def delete_conversation(self, conversation_id: str) -> bool:
        result = await self.session.execute(
            delete(Conversation).where(Conversation.id == conversation_id)
        )
        await self.session.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.info("Deleted conversation %s", conversation_id)
        return deleted

    # --- Messages -----------------------------------------------------------
    async def add_message(
        self, conversation_id: str, *, role: str, content: str
    ) -> Message:
        message = Message(
            conversation_id=conversation_id, role=role, content=content
        )
        self.session.add(message)
        # Touch the parent so it sorts to the top of the list.
        conversation = await self.get_conversation(conversation_id)
        if conversation is not None:
            # Auto-title from the first user message.
            if role == "user" and (
                not conversation.title or conversation.title == "New conversation"
            ):
                conversation.title = _derive_title(content)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_history_for_llm(
        self, conversation_id: str
    ) -> list[dict[str, str]]:
        """Return recent messages formatted for the Anthropic Messages API."""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        messages = list(result.scalars().all())
        trimmed = messages[-MAX_HISTORY_MESSAGES:]
        return [{"role": m.role, "content": m.content} for m in trimmed]


def _derive_title(text: str, *, max_len: int = 60) -> str:
    """Create a short conversation title from the first user message."""
    single_line = " ".join(text.strip().split())
    if len(single_line) <= max_len:
        return single_line or "New conversation"
    return single_line[: max_len - 1].rstrip() + "…"
