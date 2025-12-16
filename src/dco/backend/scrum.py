import threading
import time
import os
import datetime
import re
import random
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
        self.max_iterations = 10 

    def set_project_path(self, path: str):
        if os.path.exists(path):
            self.project_path = path
            self.memory.set_project_path(path)
            print(f"[ScrumMaster] Context: {path}")

    def start_sprint(self, task_name: str):
        if self.state != "IDLE" and self.state != "AWAITING_USER":
             print(f"[ScrumMaster] Busy ({self.state})")
             return
        
        is_continuation = (self.state == "AWAITING_USER")
        
        workflow_thread = threading.Thread(
            target=self._run_autonomous_loop, 
            args=(task_name, is_continuation)
        )
        workflow_thread.start()

    def _set_state(self, new_state):
        self.state = new_state
        # Optional: Broadcast logic here

    def get_latest_question(self):
        """Reads the last entry from the Huddle to show the user."""
        try:
            huddle_path = os.path.join(self.project_path, ".brain/HUDDLE.md")
            with open(huddle_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # Get the last non-empty line
            for line in reversed(lines):
                if line.strip():
                    return line.strip()
            return "Agents requested input."
        except:
            return "Check HUDDLE.md for details."

    def _run_autonomous_loop(self, task_payload: str, is_continuation: bool):
        iteration = 0
        
        if is_continuation:
            self._append_to_huddle("User", task_payload)
            print("▶️ [ScrumMaster] Resuming Mission with User Feedback...")
        else:
            self.initialize_huddle(task_payload)
            print("🚀 [ScrumMaster] Starting New Mission...")
            
            self._set_state("PLANNING")
            self._run_agent("claude", "NAVIGATOR", task_payload)
            self.sm.wait_for_process("claude")

        while iteration < self.max_iterations:
            iteration += 1
            
            # 1. BUILD
            self._set_state("BUILDING")
            self._run_agent("codex", "DRIVER", "Follow instructions in HUDDLE.md")
            self.sm.wait_for_process("codex")

            # 2. REVIEW
            self._set_state("REVIEWING")
            self._run_agent("claude", "REVIEWER", "Review the implementation in HUDDLE.md")
            self.sm.wait_for_process("claude")

            # 3. CHECK STATUS
            status = self._analyze_huddle_status()
            
            if status == "COMPLETED":
                print("✅ [ScrumMaster] Mission Accomplished.")
                self._set_state("IDLE")
                break
            elif status == "USER_INPUT_REQUIRED":
                # Only stop if explicitly requested
                self._set_state("AWAITING_USER")
                return 
            else:
                # Default: Loop continues
                pass

        if iteration >= self.max_iterations:
            print("🛑 [ScrumMaster] Max iterations reached.")
            self._set_state("AWAITING_USER")

    def _analyze_huddle_status(self):
        try:
            huddle_path = os.path.join(self.project_path, ".brain/HUDDLE.md")
            with open(huddle_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            
            recent_log = content[-1000:] 
            if "STATUS: COMPLETED" in recent_log:
                return "COMPLETED"
            if "STATUS: NEEDS_INPUT" in recent_log:
                return "USER_INPUT_REQUIRED"
            return "CONTINUE"
        except:
            return "CONTINUE"

    def initialize_huddle(self, task_name: str):
        path = os.path.join(self.project_path, ".brain/HUDDLE.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%H:%M")
        header = f"# Mission: {task_name}\n> Started: {timestamp}\n\n**System:** Mission initialized.\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(header)

    def _append_to_huddle(self, agent: str, message: str):
        path = os.path.join(self.project_path, ".brain/HUDDLE.md")
        timestamp = datetime.datetime.now().strftime("%H:%M")
        entry = f"\n\n**{agent} ({timestamp}):** {message}\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(entry)

    def _run_agent(self, agent_name: str, role: str, task: str):
        huddle_path_rel = ".brain/HUDDLE.md"
        
        # --- PROMPTS ---
        if role == "NAVIGATOR":
            prompt = (
                f"ROLE: ARCHITECT. TASK: {task}.\n"
                f"ACTION: Read `.brain/SKILLS.md`. Write a plan in `{huddle_path_rel}`."
            )
        elif role == "DRIVER":
            prompt = (
                f"ROLE: BUILDER. ACTION: Read `{huddle_path_rel}`. Implement the pending tasks."
            )
        elif role == "REVIEWER":
            prompt = (
                f"ROLE: QA. ACTION: Check the recent code changes.\n"
                f"- If success, write 'STATUS: COMPLETED' to `{huddle_path_rel}`.\n"
                f"- If bugs, describe them in `{huddle_path_rel}` for the Driver.\n"
                f"- If you need the user, write 'STATUS: NEEDS_INPUT'."
            )

        cmd = ["claude" if agent_name == "claude" else "codex", "--print" if agent_name == "claude" else "-p", prompt]
        
        if ENABLE_REAL_AGENTS:
            self.sm.start_subprocess(agent_name, cmd, cwd=self.project_path)
        else:
            # --- SIMULATION LOGIC (Updated to loop) ---
            # Randomly finish after a few steps or ask for input
            outcome = random.choice(["STATUS: COMPLETED", "Fixing bugs...", "Fixing bugs...", "STATUS: NEEDS_INPUT"])
            msg = f"Analyzing... {outcome}"
            
            if role == "REVIEWER":
                # Ensure we don't just stop immediately every time in simulation
                mock_cmd = f"echo '[{role}] Reviewing...'; sleep 1; echo '{msg}' >> {huddle_path_rel}"
            else:
                mock_cmd = f"echo '[{role}] Coding...'; sleep 1; echo 'Work done.' >> {huddle_path_rel}"
                
            self.sm.start_subprocess(agent_name, ["bash", "-c", mock_cmd], cwd=self.project_path)