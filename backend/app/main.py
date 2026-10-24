from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.database import initialize_database
from app import config
from app.routes.auth import router as auth_router
from app.routes.health import router as health_router
from app.routes.leads import router as leads_router
from app.routes.webhook import router as webhook_router
from app.services.auth import authenticate_websocket_ticket
from app.services.websocket_manager import websocket_manager


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Meta Lead Ads PoC API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Hub-Signature-256"],
)
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(leads_router)
app.include_router(webhook_router)


@app.websocket("/ws/leads")
async def websocket_endpoint(websocket: WebSocket) -> None:
    try:
        authenticate_websocket_ticket(websocket.query_params.get("ticket", ""))
    except HTTPException:
        await websocket.accept()
        await websocket.close(code=4401, reason="Authentication required")
        return
    await websocket_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)