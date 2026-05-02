from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import logging
import asyncio
import zmq
import zmq.asyncio
from typing import Dict, List
import json
import sys
import asyncio

# [AURA-STRICT-PROTOCOL] Fix for Windows ZMQ / Uvicorn Event Loop Warning
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# [AURA-STRICT-PROTOCOL] Phase 1 - FastAPI Backend Core (ZMQ & WebSockets)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# ZMQ Background Task
async def zmq_listener():
    context = zmq.asyncio.Context()
    socket = context.socket(zmq.PULL)
    socket.bind("tcp://127.0.0.1:5555")  # Listen for MT5 Master EA
    print("[AURA] ZMQ Pipeline Active on port 5555.")
    
    while True:
        try:
            message = await socket.recv_string()
            # Broadcast raw MT5 ticks to the Next.js Dashboard via WebSockets
            await manager.broadcast(message)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[ZMQ Error] {e}")

# Modern FastAPI Lifespan Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n[AURA] Booting FastAPI Backend Core on port 8000...")
    zmq_task = asyncio.create_task(zmq_listener())
    yield
    zmq_task.cancel()
    print("\n[AURA] Shutting down FastAPI Backend Core...")

app = FastAPI(title="AURA Core Backend", lifespan=lifespan)

# Allow Next.js (usually running on port 3000) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We don't really expect Next.js to send info here, just listen
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/v1/status")
async def get_status():
    return {
        "status": "online",
        "zmq_status": "listening",
        "websocket_clients": len(manager.active_connections)
    }
