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
memory_core = MemoryCore()
scrum_master = ScrumMaster(subprocess_manager, memory_core)

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
@app.on_event("startup")
async def startup_event():
    try:
        loop = asyncio.get_running_loop()
        def async_log_bridge(agent, message):
             payload = json.dumps({"agent": agent, "message": message})
             asyncio.run_coroutine_threadsafe(manager.broadcast(payload), loop)
             
        subprocess_manager.register_callback(async_log_bridge)
    except:
        pass

# --- API MODELS ---
class MissionRequest(BaseModel):
    task: str
    project_path: str = "."  # Default to current directory

class HuddleUpdateRequest(BaseModel):
    content: str
    agent: str

# --- ENDPOINTS ---

@app.post("/start_mission")
async def start_mission(request: MissionRequest):
    """Triggers the Scrum Master to start a sprint in the specific folder."""
    
    # 1. Set the context to the requested folder (Important!)
    scrum_master.set_project_path(request.project_path)
    
    # 2. Start the sprint
    scrum_master.start_sprint(request.task)
    
    return {
        "status": "Mission Started", 
        "task": request.task, 
        "working_dir": request.project_path
    }

@app.post("/update_huddle")
async def update_huddle(request: HuddleUpdateRequest):
    # Use the dynamic project path from scrum_master
    path = os.path.join(scrum_master.project_path, ".brain/HUDDLE.md")
    
    import datetime
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    entry = f"\n\n**{request.agent} ({timestamp}):** {request.content}"
    
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(entry)
        return {"status": "Huddle Updated"}
    except Exception as e:
        return {"status": "Error", "message": str(e)}

@app.get("/huddle")
async def get_huddle():
    """Serves the HUDDLE.md content from the active project."""
    if not scrum_master.project_path:
        return "No project selected."
        
    path = os.path.join(scrum_master.project_path, ".brain/HUDDLE.md")
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