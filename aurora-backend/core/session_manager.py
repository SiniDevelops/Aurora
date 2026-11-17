from typing import List, Optional, Any
import uuid
from data.models import ChatSession, ChatMessage


class SessionManager:
    """Manages chat sessions and message history backed by SQLite."""
    
    def __init__(self, sqlite_store: Any):
        self.sqlite_store = sqlite_store
        
    async def create_session(self, vault_path: str = "", session_id: Optional[str] = None) -> ChatSession:
        """Create a new chat session and persist it to SQLite."""
        sid = session_id or str(uuid.uuid4())
        session = ChatSession(id=sid, vault_path=vault_path)
        if self.sqlite_store:
            await self.sqlite_store.create_session(session)
        return session
        
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Retrieve a session by ID with message history loaded."""
        if not self.sqlite_store:
            return None
        session = await self.sqlite_store.get_session(session_id)
        if session:
            session.messages = await self.get_history(session_id)
        return session
        
    async def get_or_create_session(self, session_id: Optional[str], vault_path: str = "") -> ChatSession:
        """Get existing session or create a new one."""
        if session_id:
            session = await self.get_session(session_id)
            if session:
                return session
            return await self.create_session(vault_path=vault_path, session_id=session_id)
        return await self.create_session(vault_path=vault_path)
        
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        skill_used: Optional[str] = None,
        tokens_used: int = 0,
        metadata: Optional[dict] = None,
    ) -> ChatMessage:
        """Add a message to the session and persist it to SQLite."""
        msg = ChatMessage(
            role=role,
            content=content,
            skill_used=skill_used,
            tokens_used=tokens_used,
            metadata=metadata or {},
        )
        if self.sqlite_store:
            # Ensure the session exists in DB before inserting message
            existing = await self.sqlite_store.get_session(session_id)
            if not existing:
                await self.create_session(vault_path="", session_id=session_id)
            await self.sqlite_store.add_message(session_id, msg)
            if hasattr(self.sqlite_store, "update_session_timestamp"):
                await self.sqlite_store.update_session_timestamp(session_id)
        return msg
        
    async def get_history(self, session_id: str, limit: int = 50) -> List[ChatMessage]:
        """Retrieve session history from SQLite."""
        if not self.sqlite_store:
            return []
        return await self.sqlite_store.get_messages(session_id, limit=limit)
        
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session from SQLite."""
        if not self.sqlite_store:
            return False
        return await self.sqlite_store.delete_session(session_id)
        
    async def list_sessions(self) -> List[ChatSession]:
        """List all sessions from SQLite."""
        if not self.sqlite_store:
            return []
        if hasattr(self.sqlite_store, "list_sessions"):
            return await self.sqlite_store.list_sessions()
        return []
