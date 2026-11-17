"""
Tests for Chat history persistence and session management.
"""

import pytest
import os
import tempfile
import asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from data.sqlite_store import SQLiteStore
from core.session_manager import SessionManager
from api.routes.chat import router as chat_router


@pytest.fixture
async def temp_sqlite_store():
    """Create a temporary SQLiteStore instance."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = SQLiteStore(path)
    await store.initialize()
    yield store
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
async def session_manager(temp_sqlite_store):
    """Create a SessionManager instance backed by real SQLite."""
    return SessionManager(temp_sqlite_store)


class TestSessionManager:
    """Tests for SessionManager persistence with SQLiteStore."""

    @pytest.mark.asyncio
    async def test_create_and_get_session(self, session_manager):
        session = await session_manager.create_session(vault_path="/test/vault")
        assert session.id is not None
        assert session.vault_path == "/test/vault"

        retrieved = await session_manager.get_session(session.id)
        assert retrieved is not None
        assert retrieved.id == session.id
        assert retrieved.vault_path == "/test/vault"
        assert retrieved.messages == []

    @pytest.mark.asyncio
    async def test_add_messages_and_get_history(self, session_manager):
        session = await session_manager.create_session(vault_path="/test/vault")

        # Add user message
        msg1 = await session_manager.add_message(
            session_id=session.id,
            role="user",
            content="Hello AI",
        )
        assert msg1.role == "user"
        assert msg1.content == "Hello AI"

        # Add assistant message
        msg2 = await session_manager.add_message(
            session_id=session.id,
            role="assistant",
            content="Hello human!",
        )
        assert msg2.role == "assistant"
        assert msg2.content == "Hello human!"

        # Retrieve history
        history = await session_manager.get_history(session.id)
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[0].content == "Hello AI"
        assert history[1].role == "assistant"
        assert history[1].content == "Hello human!"

        # get_session also loads messages
        session_loaded = await session_manager.get_session(session.id)
        assert len(session_loaded.messages) == 2

    @pytest.mark.asyncio
    async def test_list_and_delete_sessions(self, session_manager):
        s1 = await session_manager.create_session(vault_path="/vault1")
        s2 = await session_manager.create_session(vault_path="/vault2")

        await session_manager.add_message(s1.id, "user", "Message 1")
        await session_manager.add_message(s1.id, "assistant", "Response 1")

        sessions = await session_manager.list_sessions()
        session_ids = [s.id for s in sessions]
        assert s1.id in session_ids
        assert s2.id in session_ids

        # Delete session
        deleted = await session_manager.delete_session(s1.id)
        assert deleted is True

        remaining = await session_manager.list_sessions()
        remaining_ids = [s.id for s in remaining]
        assert s1.id not in remaining_ids
        assert s2.id in remaining_ids

        # Check messages of deleted session are gone
        history = await session_manager.get_history(s1.id)
        assert len(history) == 0


class TestChatRoutesWithPersistence:
    """Tests for chat API routes saving to SQLite and loading history."""

    @pytest.fixture
    def app(self, temp_sqlite_store, session_manager):
        test_app = FastAPI()
        test_app.include_router(chat_router, prefix="/api/chat")

        mock_orchestrator = MagicMock()
        
        async def fake_process(msg, session_id, history=None):
            if history:
                return f"Resumed response to '{msg}' with {len(history)} prior messages"
            return f"Initial response to '{msg}'"

        mock_orchestrator.process_message = AsyncMock(side_effect=fake_process)

        mock_config = MagicMock()
        mock_config.vault_path = "/test/vault"

        test_app.state.session_manager = session_manager
        test_app.state.orchestrator = mock_orchestrator
        test_app.state.config = mock_config
        test_app.state.sqlite_store = temp_sqlite_store

        return test_app

    @pytest.mark.asyncio
    async def test_send_message_saves_exchange_to_sqlite(self, app, session_manager):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/chat/message", json={"message": "First message"})
            assert resp.status_code == 200
            data = resp.json()
            session_id = data["session_id"]
            assert data["response"] == "Initial response to 'First message'"

            # Verify SQLite persisted both user and assistant messages
            history = await session_manager.get_history(session_id)
            assert len(history) == 2
            assert history[0].role == "user"
            assert history[0].content == "First message"
            assert history[1].role == "assistant"
            assert history[1].content == "Initial response to 'First message'"

    @pytest.mark.asyncio
    async def test_resume_session_loads_history_and_persists_new_exchange(self, app, session_manager):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. First exchange
            resp1 = await client.post("/api/chat/message", json={"message": "What is Aurora?"})
            assert resp1.status_code == 200
            session_id = resp1.json()["session_id"]

            # 2. Resuming the session with session_id
            resp2 = await client.post(
                "/api/chat/message",
                json={"message": "Can it index notes?", "session_id": session_id}
            )
            assert resp2.status_code == 200
            data2 = resp2.json()
            assert data2["session_id"] == session_id
            # The orchestrator received the 2 prior messages!
            assert "with 2 prior messages" in data2["response"]

            # 3. Check SQLite has all 4 messages
            history = await session_manager.get_history(session_id)
            assert len(history) == 4
            assert [m.role for m in history] == ["user", "assistant", "user", "assistant"]
            assert history[2].content == "Can it index notes?"

            # 4. GET /api/chat/history/{session_id} returns all 4 messages
            hist_resp = await client.get(f"/api/chat/history/{session_id}")
            assert hist_resp.status_code == 200
            hist_data = hist_resp.json()
            assert len(hist_data["messages"]) == 4

            # 5. GET /api/chat/session/{session_id} returns session with history
            sess_resp = await client.get(f"/api/chat/session/{session_id}")
            assert sess_resp.status_code == 200
            sess_data = sess_resp.json()
            assert sess_data["session_id"] == session_id
            assert len(sess_data["messages"]) == 4

            # 6. GET /api/chat/sessions lists the session
            list_resp = await client.get("/api/chat/sessions")
            assert list_resp.status_code == 200
            sessions_list = list_resp.json()["sessions"]
            assert any(s["id"] == session_id for s in sessions_list)
