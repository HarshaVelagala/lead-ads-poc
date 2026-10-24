import json

from fastapi import WebSocket

from app.schemas.lead import LeadRead


class WebSocketManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast_lead(self, lead: LeadRead) -> None:
        payload = json.dumps({"type": "new_lead", "data": lead.model_dump(mode="json")})
        stale: list[WebSocket] = []
        for websocket in self.connections:
            try:
                await websocket.send_text(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket)


websocket_manager = WebSocketManager()