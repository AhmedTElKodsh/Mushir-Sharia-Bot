from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import json
import uuid

ws_router = APIRouter()
router = ws_router

class ConnectionManager:
    """Manage WebSocket connections."""
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self.active[session_id] = ws
        await ws.send_json({"type": "connected", "session_id": session_id})

    def disconnect(self, session_id: str):
        if session_id in self.active:
            del self.active[session_id]

    async def send_message(self, session_id: str, data: dict):
        if session_id in self.active:
            await self.active[session_id].send_json(data)

manager = ConnectionManager()

@ws_router.websocket("/ws/{session_id}")
async def websocket_endpoint(ws: WebSocket, session_id: str):
    await manager.connect(session_id, ws)
    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "unknown")
            if msg_type == "query":
                await manager.send_message(session_id, {"type": "typing"})
                # Process query via ClarificationEngine
                from src.chatbot.clarification_engine import ClarificationEngine
                from src.chatbot.session_manager import SessionManager
                manager_s = SessionManager()
                engine = ClarificationEngine()
                state = manager_s.get_session(session_id)
                if not state:
                    await manager.send_message(session_id, {"type": "error", "message": "Session not found"})
                    continue
                result = engine.process_query(state, data.get("content", ""))
                manager_s.update_session(state)
                await manager.send_message(session_id, {"type": result.get("status", "unknown"), **result})
            elif msg_type == "ping":
                await manager.send_message(session_id, {"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(session_id)
