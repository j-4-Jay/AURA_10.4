import sys
import asyncio
import zmq
import zmq.asyncio
import json
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Dict, List

# [AURA-STRICT-PROTOCOL] Fix for Windows ZMQ / Uvicorn Event Loop Warning
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Global Dictionary to hold the absolute latest MT5 state for each symbol
LATEST_MT5_STATE: Dict[str, dict] = {}

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
            except Exception:
                pass

manager = ConnectionManager()

# Global ZMQ PUSH Socket to send commands BACK to MT5
zmq_push_socket = None

async def zmq_listener():
    """Listens for incoming states from MT5 Master EA"""
    context = zmq.asyncio.Context()
    
    # Socket 1: PULL (MT5 -> Python)
    pull_socket = context.socket(zmq.PULL)
    pull_socket.bind("tcp://127.0.0.1:5555")
    print("[AURA ZMQ] PULL Socket Active on port 5555 (Receiving from MT5).")
    
    # Socket 2: PUSH (Python -> MT5)
    global zmq_push_socket
    zmq_push_socket = context.socket(zmq.PUSH)
    zmq_push_socket.bind("tcp://127.0.0.1:5556")
    print("[AURA ZMQ] PUSH Socket Active on port 5556 (Sending to MT5).")
    
    while True:
        try:
            message = await pull_socket.recv_string()
            
            # Parse the JSON to update the global memory state for the AI
            try:
                payload = json.loads(message)
                symbol = payload.get("symbol", "UNKNOWN")
                if symbol != "UNKNOWN":
                    LATEST_MT5_STATE[symbol] = payload
            except json.JSONDecodeError:
                pass
                
            # Broadcast raw MT5 ticks to the Next.js Dashboard via WebSockets
            await manager.broadcast(message)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[ZMQ Error] {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n[AURA] Booting FastAPI Backend Core on port 8000...")
    zmq_task = asyncio.create_task(zmq_listener())
    yield
    zmq_task.cancel()
    print("\n[AURA] Shutting down FastAPI Backend Core...")

app = FastAPI(title="AURA Core Backend", lifespan=lifespan)

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
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- NEW ENDPOINTS FOR PHASE 7 (LIVE AI TRADING) ---

@app.get("/api/v1/status/{symbol}")
async def get_symbol_status(symbol: str):
    """The AI calls this endpoint to get the latest chart data from MT5"""
    if symbol in LATEST_MT5_STATE:
        return LATEST_MT5_STATE[symbol]
    raise HTTPException(status_code=404, detail="No data received from MT5 for this symbol yet.")

@app.post("/api/v1/rl_signal")
async def post_rl_signal(symbol: str, action: str):
    """The AI calls this endpoint to execute a trade. We forward it to MT5 via ZMQ."""
    global zmq_push_socket
    if zmq_push_socket is None:
        raise HTTPException(status_code=500, detail="ZMQ PUSH socket not initialized.")
        
    action_payload = {
        "magic_number": 999999,  # Master AI Magic Number
        "symbol": symbol,
        "action": action.upper()  # "BUY", "SELL", or "CLOSE"
    }
    
    try:
        # Send the command directly back to the MT5 EA!
        await zmq_push_socket.send_string(json.dumps(action_payload))
        # Also broadcast the AI's action to the frontend dashboard!
        await manager.broadcast(json.dumps({"type": "AI_ACTION", "data": action_payload}))
        return {"status": "success", "message": f"Action {action} sent to MT5 for {symbol}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/status")
async def get_general_status():
    return {
        "status": "online",
        "active_symbols": list(LATEST_MT5_STATE.keys()),
        "websocket_clients": len(manager.active_connections)
    }

# --- NEW ENDPOINTS FOR MT5 WEBREQUESTS ---

# Global Dictionary to hold pending orders from AI to MT5
PENDING_MT5_ORDERS: Dict[str, str] = {}

@app.post("/api/v1/mt5/tick")
async def receive_mt5_tick(payload: dict):
    """MT5 calls this to send chart data"""
    symbol = payload.get("symbol", "UNKNOWN")
    if symbol != "UNKNOWN":
        LATEST_MT5_STATE[symbol] = payload
    
    # Broadcast to Next.js Dashboard
    await manager.broadcast(json.dumps(payload))
    return {"status": "success"}

@app.get("/api/v1/mt5/poll/{symbol}")
async def poll_mt5_orders(symbol: str):
    """MT5 calls this every tick to ask if the AI ordered a trade"""
    if symbol in PENDING_MT5_ORDERS:
        order = PENDING_MT5_ORDERS[symbol]
        del PENDING_MT5_ORDERS[symbol] # Delete so we don't double-execute
        return order
    return "NONE"

# Update the old rl_signal to use the new queue system
@app.post("/api/v1/rl_signal")
async def post_rl_signal(symbol: str, action: str):
    """The AI calls this endpoint to execute a trade."""
    
    action_payload = {
        "magic_number": 999999,
        "symbol": symbol,
        "action": action.upper()
    }
    
    # Queue the order for MT5 to fetch
    PENDING_MT5_ORDERS[symbol] = action.upper()
    
    # Broadcast to dashboard
    await manager.broadcast(json.dumps({"type": "AI_ACTION", "data": action_payload}))
    return {"status": "success"}