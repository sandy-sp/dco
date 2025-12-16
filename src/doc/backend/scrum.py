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
ENABLE_REAL_AGENTS = os.getenv("DOC_ENABLE_REAL_AGENTS", "false").lower() == "true"
CLAUDE_BIN = os.getenv("DOC_CLAUDE_BIN", "claude")
CODEX_BIN = os.getenv("DOC_CODEX_BIN", "codex")

class ScrumMaster:
    def __init__(self, subprocess_manager, memory_core: MemoryCore, broadcast_func=None):
        self.sm = subprocess_manager
        self.memory = memory_core
        self.state = "IDLE"
        self.project_path = os.getcwd()
        self.broadcast_func = broadcast_func
        self.max_iterations = 10 
        self.cartographer = Cartographer(self.project_path)
        
        # Register DB Logger to capture Agent Process Output
        self.sm.register_callback(self._capture_agent_output)

    def _capture_agent_output(self, agent: str, message: str):
        """Callback to log subprocess output to Memory."""
        # Avoid logging system/debug noise if possible, but for now capture all.
        # Filter out empty lines?
        if message.strip():
             self.memory.log_interaction(agent, message, type="agent_log")

    def set_project_path(self, path: str):
        if os.path.exists(path):
            self.project_path = path
            self.memory.set_project_path(path)
            self.cartographer.root_path = path
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
            # We fetch the latest status msg. If format is agent: msg, we return msg or whole line.
            # get_latest_status returns raw document content.
            return self.memory.get_latest_status()
        except:
            return "Check logs for details."

    def _run_autonomous_loop(self, task_payload: str, is_continuation: bool):
        iteration = 0
        
        # Maps the codebase at start of mission
        print("🗺️ [ScrumMaster] Mapping codebase...")
        # (Map generation is now handled per-agent call or we can keep it here for initial check)
        self.cartographer.save_map()
        
        if is_continuation:
            self._append_to_huddle("User", task_payload)
            print("▶️ [ScrumMaster] Resuming Mission with User Feedback...")
        else:
            self.initialize_huddle(task_payload)
            print("🚀 [ScrumMaster] Starting New Mission...")
            
            self._set_state("PLANNING")
            self._run_agent("claude", "NAVIGATOR", task_payload)
            if not self.sm.wait_for_process("claude", timeout=120):
                 print("🛑 [ScrumMaster] Planning Timed Out! Killing process...")
                 self.sm.kill_all()
                 self._set_state("AWAITING_USER")
                 return

        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n🔄 [ScrumMaster] Loop Iteration {iteration}")

            # 0. CONTEXT MAINTENANCE
            self._check_and_prune_context()

            # 1. BUILD
            self._set_state("BUILDING")
            self._run_agent("codex", "DRIVER", "Follow instructions in HUDDLE.md")
            if not self.sm.wait_for_process("codex", timeout=120):
                 print("🛑 [ScrumMaster] Build Timed Out! Killing process...")
                 self.sm.kill_all()
                 break

            # 1.5 VERIFY (Tool Use)
            self._run_verification(task_payload)

            # 2. REVIEW
            self._set_state("REVIEWING")
            self._run_agent("claude", "REVIEWER", "Review the implementation in HUDDLE.md")
            if not self.sm.wait_for_process("claude", timeout=120):
                 print("🛑 [ScrumMaster] Review Timed Out! Killing process...")
                 self.sm.kill_all()
                 break

            # 3. CHECK STATUS
            status = self._analyze_huddle_status()
            
            if status == "COMPLETED":
                print("✅ [ScrumMaster] Mission Accomplished.")
                print("🧠 [ScrumMaster] Assimilating new skills...")
                self._run_learning_phase(task_payload)
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
        """Checks if context is too large. (Handled by DB limit now, stubbed for future expansion)."""
        # With DB-based history fetching (limit=50), strict file pruning is less critical.
        # We can implement summarization later if window size becomes an issue even with limit.
        pass

    def _run_verification(self, task=None):
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
            
            report = f"Test Output:\n```\n{output.strip()[-2000:]}\n```" # Cap output size
            self._append_to_huddle("System", report)
            print(f"🧪 [ScrumMaster] Verification {status}.")
            
        except Exception as e:
            self._append_to_huddle("System", f"Verification Failed to Run: {e}")

    def _run_learning_phase(self, task: str):
        """Extracts lessons learned and saves them to SKILLS.md."""
        try:
            # Fetch robust history for learning
            content = self.memory.get_recent_huddle(limit=500)

            prompt = (
                f"Review this session log. Extract 1-3 technical 'Rules of Thumb' or 'Gotchas' we learned. "
                f"Format them as bullet points. If nothing new was learned, say 'NO_UPDATE'.\n\nLOG:\n{content}"
            )

            cmd = ["claude", "--print", prompt]
            
            if not ENABLE_REAL_AGENTS:
                output = "NO_UPDATE" # Simulation default
                # Random chance to learn something in sim
                if random.random() < 0.3:
                     output = "- Always check for null values in JSON parsing."
            else:
                 import subprocess
                 result = subprocess.run(
                    cmd, 
                    cwd=self.project_path, 
                    capture_output=True, 
                    text=True, 
                    timeout=20
                )
                 output = result.stdout.strip()

            if "NO_UPDATE" not in output:
                # Skills persist in collection
                # For now, we still write to SKILLS.md as requested OR use memory.
                # Task says "Update ScrumMaster... use memory.py for state".
                # But Step 1 of task list says "Add skills collection". 
                # Let's do both: Log to DB and keep file for visibility if desirable, or migrate fully.
                # The deliverable says "All state is persisted in .brain/memory.db".
                
                self.memory.add_memory("skills", output, metadata={"task": task, "timestamp": datetime.datetime.now().isoformat()})
                
                # Also keep SKILLS.md for human readability? The prompt implies full migration.
                # "Remove dependency on markdown files for logic". 
                # Be safe: Write to DB primarily. 
                print("🧠 [ScrumMaster] Skills updated in DB.")

            else:
                print("🧠 [ScrumMaster] No new skills extracted.")

        except Exception as e:
            print(f"⚠️ [ScrumMaster] Learning phase failed: {e}")

    def _analyze_huddle_status(self):
        try:
            recent_log = self.memory.get_latest_status()
            if "STATUS: COMPLETED" in recent_log:
                return "COMPLETED"
            if "STATUS: NEEDS_INPUT" in recent_log:
                return "USER_INPUT_REQUIRED"
            return "CONTINUE"
        except:
            return "CONTINUE"

    def initialize_huddle(self, task_name: str):
        self.memory.log_interaction("System", f"Mission: {task_name} initialized.", type="system")

    def _append_to_huddle(self, agent: str, message: str):
        self.memory.log_interaction(agent, message, type="agent" if agent not in ["User", "System"] else "system")

    def _run_agent(self, agent_name: str, role: str, task: str):
        # Fetch dynamic context
        # Provide last ~50 messages
        huddle_context = self.memory.get_recent_huddle(limit=50)
        
        # --- PROMPTS ---
        if role == "NAVIGATOR":
            self.cartographer.save_map()
            map_content = ""
            try:
                with open(os.path.join(self.project_path, ".brain/repo_map.txt"), "r") as f:
                    map_content = f.read()
            except:
                pass
            
            prompt = (
                f"ROLE: ARCHITECT. TASK: {task}.\n"
                f"ACTION: Read the history below. Write a plan if needed or proceed.\n"
                f"HISTORY:\n{huddle_context}\n"
            )
            prompt += f"\n\nCONTEXT (REPO MAP):\n{map_content}"
        elif role == "DRIVER":
            prompt = (
                f"ROLE: BUILDER. ACTION: Read history. Implement the pending tasks.\n"
                f"HISTORY:\n{huddle_context}"
            )
        elif role == "REVIEWER":
            prompt = (
                f"ROLE: QA. ACTION: Check the recent code changes.\n"
                f"- If success, output 'STATUS: COMPLETED'.\n"
                f"- If bugs, describe them.\n"
                f"- If you need the user, output 'STATUS: NEEDS_INPUT'.\n"
                f"HISTORY:\n{huddle_context}"
            )
        
        cmd = [CLAUDE_BIN if agent_name == "claude" else CODEX_BIN, "--print" if agent_name == "claude" else "-p", prompt]
        
        if ENABLE_REAL_AGENTS:
            self.sm.start_subprocess(agent_name, cmd, cwd=self.project_path)
        else:
            # --- SIMULATION LOGIC ---
            outcome = random.choice(["STATUS: COMPLETED", "Fixing bugs...", "Fixing bugs...", "STATUS: NEEDS_INPUT"])
            
            # Since we switched to DB, we simulate appending to DB via logic in loop?
            # No, correct way is: self._run_agent CALLS subprocess.
            # The subprocess (real or mocked) would output text.
            # But wait, `_run_agent` in previous code mocked via `bash -c ... echo >> HUDDLE.md`.
            # We must update the mock to NOT write to HUDDLE.md, but just output to stdout.
            # SubprocessManager captures stdout and calls `_broadcast_log`.
            # BUT: where does it get written to DB?
            # SubprocessManager broadcast calls `cli_logger`. CLI logger appends to `log_buffer`.
            # It seems `ScrumMaster` doesn't automatically capture SM output to DB?
            # Wait, `ScrumMaster` needs to capture the output and write to DB.
            # Currently `ScrumMaster` depends on `_append_to_huddle` manually or expects Agents to write to file?
            # In previous implementation, Agents (simulated) echoed into HUDDLE.md.
            # NOW: We need to capture their output.
            
            # SubprocessManager *does* capture output and calls callbacks.
            # We need to register a callback in ScrumMaster to log to memory!
            
            # I will add a callback registration in ScrumMaster.__init__ or start_sprint.
            
            msg = f"Analyzing... {outcome}"
            if role == "REVIEWER":
                 mock_cmd = f"echo '[{role}] Reviewing...'; sleep 1; echo '{msg}'"
            else:
                 mock_cmd = f"echo '[{role}] Coding...'; sleep 1; echo 'Work done.'"
                 
            self.sm.start_subprocess(agent_name, ["bash", "-c", mock_cmd], cwd=self.project_path)