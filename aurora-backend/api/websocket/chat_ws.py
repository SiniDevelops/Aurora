"""
WebSocket handler for streaming chat.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import asyncio
from typing import List, Optional
import uuid

router = APIRouter()

class ConnectionManager:
    """Manager for WebSocket connections."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and store connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove from list."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        """Send to all connections."""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

@router.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    """WebSocket endpoint for streaming chat responses."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                parsed_data = json.loads(data)
                message = parsed_data.get("message", "")
                session_id = parsed_data.get("session_id")
                
                if not session_id:
                    session_id = str(uuid.uuid4())
                
                orchestrator = websocket.app.state.orchestrator
                
                await websocket.send_text(json.dumps({"type": "start", "session_id": session_id}))
                
                # Stream response tokens
                async for token in orchestrator.stream_process_message(message, session_id):
                    await websocket.send_text(json.dumps({"type": "token", "content": token}))
                
                await websocket.send_text(json.dumps({
                    "type": "end", 
                    "skill_used": "some_skill", 
                    "tokens_used": 100
                }))
                
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON"}))
            except Exception as e:
                await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
