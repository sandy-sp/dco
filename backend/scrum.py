import threading
import time
import os
import datetime
from typing import Optional, Callable
from dotenv import load_dotenv
from .memory import MemoryCore

# Set to True to use real Claude/Codex CLI commands
# Reads from DCO_ENABLE_REAL_AGENTS env var

class ScrumMaster:
    def __init__(self, subprocess_manager, memory_core: MemoryCore):
        self.sm = subprocess_manager
        self.memory = memory_core
        self.state = "IDLE"
        self.project_path = os.getcwd()  # Default to current directory
        # Load configuration
        load_dotenv()
        self.real_mode = os.getenv("DCO_ENABLE_REAL_AGENTS", "false").lower() == "true"

    def set_project_path(self, path: str):
        """Sets the working directory for the sprint."""
        if os.path.exists(path):
            self.project_path = path
            # Update memory to point to this project's .brain
            self.memory.set_project_path(path) 
            print(f"[ScrumMaster] Switched context to: {path}")
        else:
            print(f"[ScrumMaster] Invalid path: {path}")

    def start_sprint(self, task_name: str):
        """Initiates the Sequential Twin-Turbo workflow."""
        if self.state != "IDLE":
             print(f"[ScrumMaster] Cannot start sprint. Current state: {self.state}")
             return

        print(f"[ScrumMaster] Starting Sprint: {task_name}")
        
        # 1. Initialize the Huddle (Chat Room)
        self.initialize_huddle(task_name)

        # 2. Start Phase 1: Planning (Claude)
        self.run_phase_1_planning(task_name)

    def run_phase_1_planning(self, task_name: str):
        """Phase 1: Navigator (Claude) plans the implementation."""
        self.state = "PLANNING"
        print("[ScrumMaster] Phase 1: Planning (Claude)")
        
        def on_phase_1_complete():
            print("[ScrumMaster] Phase 1 Complete. Triggering Phase 2...")
            self.run_phase_2_building(task_name)

        self._agent_runner("claude", "NAVIGATOR", task_name, on_exit=on_phase_1_complete)

    def run_phase_2_building(self, task_name: str):
        """Phase 2: Driver (Codex) builds the code."""
        self.state = "BUILDING"
        print("[ScrumMaster] Phase 2: Building (Codex)")
        
        def on_phase_2_complete():
            print("[ScrumMaster] Phase 2 Complete. Triggering Phase 3...")
            self.run_phase_3_review(task_name)

        self._agent_runner("codex", "DRIVER", task_name, on_exit=on_phase_2_complete)

    def run_phase_3_review(self, task_name: str):
        """Phase 3: Navigator (Claude) reviews the implementation."""
        self.state = "REVIEWING"
        print("[ScrumMaster] Phase 3: Review (Claude)")
        
        def on_phase_3_complete():
            print("[ScrumMaster] Sprint Complete.")
            self.state = "IDLE"
            # Optional: Notify user via log or other means

        self._agent_runner("claude", "REVIEWER", task_name, on_exit=on_phase_3_complete)

    def _get_file_path(self, relative_path):
        """Helper to get absolute path inside project."""
        return os.path.join(self.project_path, relative_path)

    def initialize_huddle(self, task_name: str):
        """Resets the HUDDLE.md file with the Sprint Goal."""
        timestamp = datetime.datetime.now().strftime("%H:%M")
        header = f"""# Sprint Huddle: {task_name}
> **Sprint Goal:** {task_name}
> **Started:** {timestamp}

**System:** Sprint initialized.
- **Phase 1 (Planning):** Claude analyzes requirements and writes plan.
- **Phase 2 (Building):** Codex implements the plan.
- **Phase 3 (Review):** Claude verifies the work.

---
"""
        huddle_path = self._get_file_path(".brain/HUDDLE.md")
        
        # Ensure .brain directory exists
        os.makedirs(os.path.dirname(huddle_path), exist_ok=True)
        
        try:
            with open(huddle_path, "w", encoding="utf-8") as f:
                f.write(header)
            print("[ScrumMaster] Huddle initialized.")
        except Exception as e:
            print(f"[ScrumMaster] Failed to init huddle: {e}")

    def prepare_context(self, task_name: str) -> str:
        """Constructs the static context (Patterns + Skills) for agents."""
        # Read System Patterns
        patterns = ""
        patterns_path = self._get_file_path(".brain/context/systemPatterns.md")
        try:
            with open(patterns_path, "r", encoding="utf-8") as f:
                patterns = f.read()
        except FileNotFoundError:
            patterns = "No system patterns found."

        # Query Vector Memory for relevant past lessons
        mem_results = self.memory.query_memory("skills", task_name)
        skills = ""
        if mem_results and 'documents' in mem_results and mem_results['documents'] and mem_results['documents'][0]:
            skills = "\n".join(mem_results['documents'][0])
        
        return f"System Patterns:\n{patterns}\n\nRelevant Skills:\n{skills}"

    def _agent_runner(self, agent_name: str, role: str, task_name: str, on_exit: Optional[Callable[[], None]] = None):
        """Simulates an agent's lifecycle with Role-Specific Prompts."""
        print(f"[ScrumMaster] Summoning {agent_name} as {role}...")
        
        base_context = self.prepare_context(task_name)
        huddle_path_rel = ".brain/HUDDLE.md" # Relative to cwd
        
        prompt = ""
        cmd_list = []

        # --- ROLE-SPECIFIC PROMPT ENGINEERING ---
        if role == "NAVIGATOR":
            # Phase 1
            prompt = (
                f"ROLE: NAVIGATOR (Architect). TASK: {task_name}.\n"
                f"{base_context}\n\n"
                "INSTRUCTIONS:\n"
                f"1. Analyze the task and architecture.\n"
                f"2. Write a step-by-step implementation plan in `{huddle_path_rel}`.\n"
                "3. Address existing files and required changes."
            )
            cmd_list = ["claude", "--print", prompt]
            
        elif role == "DRIVER":
            # Phase 2
            prompt = (
                f"ROLE: DRIVER (Builder). TASK: {task_name}.\n"
                f"{base_context}\n\n"
                "INSTRUCTIONS:\n"
                f"1. Read `{huddle_path_rel}` to understand the Navigator's plan.\n"
                "2. Implement the requested code files immediately.\n"
                "3. Do not ask clarifying questions; infer from the plan.\n"
                f"4. Log your progress to `{huddle_path_rel}`."
            )
            cmd_list = ["codex", "-p", prompt]
        
        elif role == "REVIEWER":
            # Phase 3
            prompt = (
                f"ROLE: REVIEWER (QA). TASK: {task_name}.\n"
                f"{base_context}\n\n"
                "INSTRUCTIONS:\n"
                f"1. Read the newly created code files.\n"
                f"2. Compare them against the plan in `{huddle_path_rel}`.\n"
                "3. If there are bugs, fix them or report them in the huddle.\n"
                "4. If success, mark the sprint as COMPLETED."
            )
            cmd_list = ["claude", "--print", prompt]

        # --- EXECUTION ---
        if self.real_mode:
            self.sm.start_subprocess(agent_name, cmd_list, cwd=self.project_path, on_exit=on_exit)
        else:
            # Simulation Mode
            self._run_simulation(agent_name, role, on_exit)

    def _run_simulation(self, agent_name, role, on_exit):
        """Mock output for testing."""
        mock_action = ""
        if role == "NAVIGATOR":
            mock_action = (
                f"echo '[{agent_name}] Planning phase started...'; sleep 1; "
                f"echo '[{agent_name}] Writing Plan to HUDDLE.md...'; "
                f"echo '\n**Claude (Navigator):** Plan created.' >> .brain/HUDDLE.md; "
                f"sleep 1; echo '[{agent_name}] Planning complete.'"
            )
        elif role == "DRIVER":
            mock_action = (
                f"echo '[{agent_name}] Reading plan...'; sleep 1; "
                f"echo '[{agent_name}] Coding features...'; "
                f"echo '\n**Codex (Driver):** Code implemented.' >> .brain/HUDDLE.md; "
                f"sleep 1; echo '[{agent_name}] Build complete.'"
            )
        elif role == "REVIEWER":
             mock_action = (
                f"echo '[{agent_name}] Reviewing code...'; sleep 1; "
                f"echo '[{agent_name}] All checks passed.'; "
                f"echo '\n**Claude (Reviewer):** Sprint Verified.' >> .brain/HUDDLE.md; "
                f"sleep 1; echo '[{agent_name}] Review complete.'"
            )

        # Run simulation in the correct folder too
        self.sm.start_subprocess(agent_name, ["bash", "-c", mock_action], cwd=self.project_path, on_exit=on_exit)