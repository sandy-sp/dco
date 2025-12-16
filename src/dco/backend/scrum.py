import threading
import time
import os
import datetime
import re
import random
from .memory import MemoryCore
from .cartographer import Cartographer
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
        self.cartographer = None

    def set_project_path(self, path: str):
        if os.path.exists(path):
            self.project_path = path
            self.memory.set_project_path(path)
            self.cartographer = Cartographer(path)
            print(f"[ScrumMaster] Context: {path}")

    def start_sprint(self, task_name: str):
        if self.state != "IDLE" and self.state != "AWAITING_USER":
             print(f"[ScrumMaster] Busy ({self.state})")
             return
        
        is_continuation = (self.state == "AWAITING_USER")
        
        # Ensure cartographer is ready
        if not self.cartographer:
            self.cartographer = Cartographer(self.project_path)

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
        
        # Maps the codebase at start of mission
        print("🗺️ [ScrumMaster] Mapping codebase...")
        self.cartographer.save_map()
        
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
            print(f"\n🔄 [ScrumMaster] Loop Iteration {iteration}")

            # 0. CONTEXT MAINTENANCE
            self._check_and_prune_context()

            # 1. BUILD
            self._set_state("BUILDING")
            self._run_agent("codex", "DRIVER", "Follow instructions in HUDDLE.md")
            self.sm.wait_for_process("codex")

            # 1.5 VERIFY (Tool Use)
            self._run_verification()

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

    def _check_and_prune_context(self):
        """Checks if HUDDLE.md is too large and summarizes it if so."""
        huddle_path = os.path.join(self.project_path, ".brain/HUDDLE.md")
        if not os.path.exists(huddle_path):
            return

        try:
            with open(huddle_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            if len(lines) > 200:
                print("✂️ [ScrumMaster] Context Pruning Triggered (Lines > 200)")
                
                # 1. Summarize content via Agent (using subprocess for simplicity to get output)
                content = "".join(lines)
                summary_prompt = (
                    f"ACTION: Summarize the following session log. Focus on pending tasks and current status. "
                    f"Discard completed steps.\n\nLOG:\n{content[-4000:]}" # Send last 4k chars to fit context
                )
                
                # We need a way to get the summary text back. check_output is useful here.
                # Assuming 'claude --print' outputs just the response.
                import subprocess
                cmd = ["claude", "--print", summary_prompt]
                if not ENABLE_REAL_AGENTS:
                    summary = "Context Summarized.\n- Pending: Check bugs.\n- Status: In Progress."
                else:
                    try:
                        result = subprocess.run(
                            cmd, 
                            cwd=self.project_path, 
                            capture_output=True, 
                            text=True, 
                            timeout=20
                        )
                        summary = result.stdout.strip()
                    except:
                        summary = "Context Summarized (Auto)."

                # 2. Archive Old Huddle
                self.memory.archive_huddle(content)
                
                # 3. Overwrite Huddle with Summary
                timestamp = datetime.datetime.now().strftime("%H:%M")
                new_huddle = (
                    f"# Mission Continuation\n> Pruned: {timestamp}\n\n"
                    f"**System:** Previous context archived. Summary:\n"
                    f"{summary}\n\n"
                    f"**System:** Resuming flow.\n"
                )
                
                with open(huddle_path, "w", encoding="utf-8") as f:
                    f.write(new_huddle)
                    
                print("✂️ [ScrumMaster] Context Pruned & Archived.")
        except Exception as e:
            print(f"⚠️ [ScrumMaster] Pruning failed: {e}")

    def _run_verification(self):
        """Runs automated tests and reports results to the Huddle."""
        print("🧪 [ScrumMaster] Running Verification...")
        
        # Detect project type
        cmd = None
        if os.path.exists(os.path.join(self.project_path, "package.json")):
            cmd = ["npm", "test"]
        elif os.path.exists(os.path.join(self.project_path, "requirements.txt")) or \
             any(f.endswith(".py") for f in os.listdir(self.project_path)):
            cmd = ["pytest"]
        
        if not cmd:
            self._append_to_huddle("System", "No tests detected (no package.json or requirements.txt). Skipping verification.")
            return

        # Run Verification
        try:
            import subprocess
            result = subprocess.run(
                cmd, 
                cwd=self.project_path, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            output = result.stdout + "\n" + result.stderr
            status = "PASSED" if result.returncode == 0 else "FAILED"
            
            report = f"Verification Results ({status}):\n```\n{output.strip()[-2000:]}\n```" # Cap output size
            self._append_to_huddle("System", report)
            print(f"🧪 [ScrumMaster] Verification {status}.")
            
        except Exception as e:
            self._append_to_huddle("System", f"Verification Failed to Run: {e}")

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
            map_content = ""
            try:
                with open(os.path.join(self.project_path, ".brain/repo_map.txt"), "r") as f:
                    map_content = f.read()
            except:
                pass

            prompt = (
                f"ROLE: ARCHITECT. TASK: {task}.\n"
                f"CONTEXT MAP:\n{map_content}\n"
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