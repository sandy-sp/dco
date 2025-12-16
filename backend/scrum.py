import threading
import time
import os
import datetime
import re
from .memory import MemoryCore
from dotenv import load_dotenv

load_dotenv()
ENABLE_REAL_AGENTS = os.getenv("DCO_ENABLE_REAL_AGENTS", "false").lower() == "true"

class ScrumMaster:
    def __init__(self, subprocess_manager, memory_core: MemoryCore, broadcast_func=None):
        self.sm = subprocess_manager
        self.memory = memory_core
        self.state = "IDLE"
        self.project_path = os.getcwd()
        self.broadcast_func = broadcast_func
        self.max_iterations = 5  # Safety brake

    def set_project_path(self, path: str):
        if os.path.exists(path):
            self.project_path = path
            self.memory.set_project_path(path)
            print(f"[ScrumMaster] Context: {path}")

    def start_sprint(self, task_name: str):
        if self.state != "IDLE":
             print(f"[ScrumMaster] Busy ({self.state})")
             return
        
        # Run in thread to keep non-blocking
        workflow_thread = threading.Thread(target=self._run_autonomous_loop, args=(task_name,))
        workflow_thread.start()

    def _set_state(self, new_state):
        self.state = new_state
        print(f"[ScrumMaster] State Change: {new_state}")
        if self.broadcast_func:
            # If connected to Web UI, notify it (optional feature now)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                asyncio.run_coroutine_threadsafe(
                    self.broadcast_func({"type": "state_change", "state": new_state}), loop
                )
            except:
                pass

    def _run_autonomous_loop(self, task_name: str):
        self.initialize_huddle(task_name)
        iteration = 0
        
        # --- PHASE 1: INITIAL PLANNING ---
        self._set_state("PLANNING")
        self._run_agent("claude", "NAVIGATOR", task_name)
        self.sm.wait_for_process("claude")

        # --- PHASE 2: THE BUILD-REVIEW LOOP ---
        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n🔄 [ScrumMaster] Iteration {iteration}/{self.max_iterations}")

            # 1. BUILD
            self._set_state("BUILDING")
            self._run_agent("codex", "DRIVER", task_name)
            self.sm.wait_for_process("codex")

            # 2. REVIEW
            self._set_state("REVIEWING")
            self._run_agent("claude", "REVIEWER", task_name)
            self.sm.wait_for_process("claude")

            # 3. ANALYZE STATUS (Read HUDDLE.md last entry)
            status = self._analyze_huddle_status()
            
            if status == "COMPLETED":
                print("✅ [ScrumMaster] Task marked completed by Navigator.")
                break
            elif status == "USER_INPUT_REQUIRED":
                print("⚠️ [ScrumMaster] Agents need user input.")
                self._set_state("AWAITING_USER")
                return # Exit loop, wait for user to re-trigger
            else:
                print("🔧 [ScrumMaster] Fixes requested. Restarting Build cycle.")
                # Loop continues

        self._set_state("IDLE")
        print("[ScrumMaster] Mission End.")

    def _analyze_huddle_status(self):
        """Reads the last few lines of HUDDLE.md to determine next step."""
        try:
            huddle_path = os.path.join(self.project_path, ".brain/HUDDLE.md")
            with open(huddle_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            
            # Simple heuristic parsing of the last message
            last_lines = content[-500:] 
            if "STATUS: COMPLETED" in last_lines:
                return "COMPLETED"
            if "STATUS: NEEDS_INPUT" in last_lines:
                return "USER_INPUT_REQUIRED"
            return "CONTINUE"
        except:
            return "CONTINUE"

    def initialize_huddle(self, task_name: str):
        path = os.path.join(self.project_path, ".brain/HUDDLE.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        header = f"# Mission: {task_name}\n**System:** Init.\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(header)

    def _run_agent(self, agent_name: str, role: str, task: str):
        huddle_file = ".brain/HUDDLE.md"
        
        # --- PROMPT STRATEGY FOR CONTINUOUS LOOP ---
        if role == "NAVIGATOR":
            prompt = (
                f"ROLE: ARCHITECT. TASK: {task}.\n"
                f"ACTION: Write a plan in `{huddle_file}`."
            )
        elif role == "DRIVER":
            prompt = (
                f"ROLE: BUILDER. TASK: {task}.\n"
                f"ACTION: Read `{huddle_file}`. Implement the LATEST requested changes/fixes."
            )
        elif role == "REVIEWER":
            prompt = (
                f"ROLE: QA. TASK: {task}.\n"
                f"ACTION: Check the code. \n"
                f"- If it works, append 'STATUS: COMPLETED' to `{huddle_file}`.\n"
                f"- If bugs exist, describe them in `{huddle_file}` for the Builder.\n"
                f"- If you need the human, append 'STATUS: NEEDS_INPUT'."
            )

        cmd = ["claude" if agent_name == "claude" else "codex", "--print" if agent_name == "claude" else "-p", prompt]
        
        if ENABLE_REAL_AGENTS:
            self.sm.start_subprocess(agent_name, cmd, cwd=self.project_path)
        else:
            # Simulation
            self.sm.start_subprocess(agent_name, ["bash", "-c", f"echo '[{role}] Working...'; sleep 2; echo 'Done'"], cwd=self.project_path)