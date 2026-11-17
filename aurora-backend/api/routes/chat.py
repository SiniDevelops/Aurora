"""
Chat API routes for Aurora backend.

Endpoints:
- POST /message — Send a message, get AI response
- GET /history/{session_id} — Get chat history
- GET /session/{session_id} — Get session details and history
- DELETE /session/{session_id} — Delete a session
- GET /sessions — List all sessions
"""

from typing import Optional, Any
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    """Request body for sending a chat message."""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""
    response: str
    session_id: str
    skill_used: Optional[str] = None
    tokens_used: int = 0


@router.post("/message", response_model=ChatResponse)
async def send_message(request: Request, chat_request: ChatRequest):
    """Send a chat message and get an AI response."""
    try:
        session_manager = request.app.state.session_manager
        orchestrator = request.app.state.orchestrator
        config = request.app.state.config

        # Check if resuming an existing session and load its history
        loaded_history = []
        if chat_request.session_id:
            existing_session = await session_manager.get_session(chat_request.session_id)
            if existing_session:
                loaded_history = await session_manager.get_history(chat_request.session_id)

        # Get or create session
        session = await session_manager.get_or_create_session(
            chat_request.session_id,
            vault_path=config.vault_path,
        )
        session_id = session.id

        # Save user message to SQLite via session_manager
        await session_manager.add_message(
            session_id=session_id,
            role="user",
            content=chat_request.message,
        )

        # Process through orchestrator pipeline with loaded history context
        response_text = await orchestrator.process_message(
            chat_request.message, session_id, history=loaded_history
        )

        # Save assistant response to SQLite via session_manager
        await session_manager.add_message(
            session_id=session_id,
            role="assistant",
            content=response_text,
        )

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            skill_used=None,  # TODO: extract from orchestrator state
            tokens_used=0,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_history(request: Request, session_id: str):
    """Get chat history for a session."""
    try:
        session_manager = request.app.state.session_manager
        messages = await session_manager.get_history(session_id)
        return {
            "session_id": session_id,
            "messages": [msg.model_dump() if hasattr(msg, 'model_dump') else msg for msg in messages],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session(request: Request, session_id: str):
    """Get session details and chat history for a resumed session."""
    try:
        session_manager = request.app.state.session_manager
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        messages = await session_manager.get_history(session_id)
        return {
            "session_id": session.id,
            "created_at": str(session.created_at) if hasattr(session, 'created_at') else None,
            "updated_at": str(session.updated_at) if hasattr(session, 'updated_at') else None,
            "vault_path": session.vault_path,
            "messages": [msg.model_dump() if hasattr(msg, 'model_dump') else msg for msg in messages],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def delete_session(request: Request, session_id: str):
    """Delete a chat session."""
    try:
        session_manager = request.app.state.session_manager
        success = await session_manager.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "deleted", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_sessions(request: Request):
    """List all chat sessions."""
    try:
        session_manager = request.app.state.session_manager
        sessions = await session_manager.list_sessions()
        return {
            "sessions": [
                {
                    "id": s.id,
                    "created_at": str(s.created_at) if hasattr(s, 'created_at') else None,
                    "message_count": len(s.messages) if hasattr(s, 'messages') else 0,
                }
                for s in sessions
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
