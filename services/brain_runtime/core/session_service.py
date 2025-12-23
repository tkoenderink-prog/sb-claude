"""Session service for managing chat sessions and message history."""

import uuid
from datetime import datetime, date, timezone
from typing import Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.db_models import ChatSessionDB, ChatMessageDB


def serialize_for_json(obj: Any) -> Any:
    """Recursively serialize objects for JSON storage, handling datetime objects."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    else:
        return obj


class SessionService:
    """Service for managing chat sessions and messages."""

    def __init__(self, db: AsyncSession):
        """
        Initialize session service.

        Args:
            db: Database session
        """
        self.db = db

    async def get_or_create_session(
        self,
        session_id: Optional[str],
        mode: str,
        provider: str,
        model: str,
        attached_skills: list[str],
    ) -> Tuple[str, bool]:
        """
        Get existing session or create a new one.

        Args:
            session_id: Optional session ID to retrieve
            mode: Chat mode ('quick', 'tools', 'agent')
            provider: Provider name ('anthropic', 'openai')
            model: Model ID
            attached_skills: List of attached skill IDs

        Returns:
            Tuple of (session_id, is_new)
        """
        # If session_id provided, try to get it
        if session_id:
            result = await self.db.execute(
                select(ChatSessionDB).where(ChatSessionDB.id == uuid.UUID(session_id))
            )
            session = result.scalar_one_or_none()

            if session:
                # Update existing session
                session.updated_at = datetime.now(timezone.utc)
                session.attached_skills = attached_skills
                await self.db.flush()
                return session_id, False

        # Create new session
        new_session_id = session_id or str(uuid.uuid4())
        session = ChatSessionDB(
            id=uuid.UUID(new_session_id),
            mode=mode,
            provider=provider,
            model=model,
            attached_skills=attached_skills,
        )
        self.db.add(session)
        await self.db.flush()

        return new_session_id, True

    async def load_messages(self, session_id: str) -> list[dict]:
        """
        Load all messages for a session.

        Args:
            session_id: Session ID

        Returns:
            List of message dictionaries with role and content
        """
        result = await self.db.execute(
            select(ChatMessageDB)
            .where(ChatMessageDB.session_id == uuid.UUID(session_id))
            .order_by(ChatMessageDB.created_at.asc())
        )
        messages = result.scalars().all()

        return [{"role": msg.role, "content": msg.content} for msg in messages]

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[list] = None,
        tool_results: Optional[list] = None,
        file_refs: Optional[list] = None,
    ) -> None:
        """
        Save a message to the database.

        Args:
            session_id: Session ID
            role: Message role ('user', 'assistant', 'system', 'tool')
            content: Message content
            tool_calls: Optional list of tool calls
            tool_results: Optional list of tool results
            file_refs: Optional list of file references
        """
        # Serialize datetime objects in tool_calls and tool_results for JSON storage
        serialized_tool_calls = serialize_for_json(tool_calls) if tool_calls else None
        serialized_tool_results = serialize_for_json(tool_results) if tool_results else None
        serialized_file_refs = serialize_for_json(file_refs) if file_refs else None

        db_message = ChatMessageDB(
            session_id=uuid.UUID(session_id),
            role=role,
            content=content,
            tool_calls=serialized_tool_calls,
            tool_results=serialized_tool_results,
            file_refs=serialized_file_refs,
        )
        self.db.add(db_message)
        await self.db.flush()

    async def get_session(self, session_id: str) -> Optional[dict]:
        """
        Get session details with messages.

        Args:
            session_id: Session ID

        Returns:
            Session dictionary with messages, or None if not found
        """
        result = await self.db.execute(
            select(ChatSessionDB).where(ChatSessionDB.id == uuid.UUID(session_id))
        )
        session = result.scalar_one_or_none()

        if not session:
            return None

        # Load messages
        messages = await self.load_messages(session_id)

        session_dict = session.to_dict()
        session_dict["messages"] = messages

        return session_dict

    async def update_injected_skills(
        self,
        session_id: str,
        injected_skills: list[str],
    ) -> None:
        """
        Update the injected skills for a session.

        Args:
            session_id: Session ID
            injected_skills: List of injected skill IDs
        """
        result = await self.db.execute(
            select(ChatSessionDB).where(ChatSessionDB.id == uuid.UUID(session_id))
        )
        session = result.scalar_one_or_none()

        if session:
            session.injected_skills = injected_skills
            await self.db.flush()
