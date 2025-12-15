from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import asyncio
import json
import os
from .subprocess_manager import SubprocessManager
from .scrum import ScrumMaster
from .memory import MemoryCore

app = FastAPI(title="DCO Orchestrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Singletons
subprocess_manager = SubprocessManager()
scrum_master = ScrumMaster(subprocess_manager)
memory_core = MemoryCore()

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# Bridge SubprocessManager logs to WebSockets
def log_bridge(agent: str, message: str):
    """Callback function that pushes logs to the WS manager."""
    payload = json.dumps({"agent": agent, "message": message})
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
             asyncio.run_coroutine_threadsafe(manager.broadcast(payload), loop)
        else:
             pass
    except RuntimeError:
        pass

# Hack: Capture loop at startup to allow threads to schedule async tasks
@app.on_event("startup")
async def startup_event():
    # Only works if running in main thread loop
    try:
        loop = asyncio.get_running_loop()
        def async_log_bridge(agent, message):
             payload = json.dumps({"agent": agent, "message": message})
             asyncio.run_coroutine_threadsafe(manager.broadcast(payload), loop)
             
        subprocess_manager.register_callback(async_log_bridge)
    except:
        pass

class MissionRequest(BaseModel):
    task: str

@app.post("/start_mission")
async def start_mission(request: MissionRequest):
    """Triggers the Scrum Master to start a sprint."""
    scrum_master.start_sprint(request.task)
    return {"status": "Mission Started", "task": request.task}

@app.get("/huddle")
async def get_huddle():
    """Serves the HUDDLE.md content."""
    path = ".brain/HUDDLE.md"
    if os.path.exists(path):
        return FileResponse(path)
    return "No active huddle."

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
