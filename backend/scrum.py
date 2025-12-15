import threading
import time
import os
import datetime
from .memory import MemoryCore

# Set to True to use real Claude/Codex CLI commands
ENABLE_REAL_AGENTS = False 

class ScrumMaster:
    def __init__(self, subprocess_manager, memory_core: MemoryCore):
        self.sm = subprocess_manager
        self.memory = memory_core
        self.state = "IDLE"
        self.project_path = os.getcwd()  # Default to current directory

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
        """Initiates the Navigator-Driver workflow."""
        if self.state != "IDLE":
             print(f"[ScrumMaster] Cannot start sprint. Current state: {self.state}")
             return

        print(f"[ScrumMaster] Starting Sprint: {task_name}")
        self.state = "SPRINTING"
        
        # 1. Initialize the Huddle (Chat Room)
        self.initialize_huddle(task_name)

        # 2. Assign Roles & Start Threads
        # Claude = Navigator (Plans & Reviews)
        # Codex = Driver (Writes Code)
        t_claude = threading.Thread(target=self._agent_runner, args=("claude", "NAVIGATOR", task_name))
        t_codex = threading.Thread(target=self._agent_runner, args=("codex", "DRIVER", task_name))
        
        t_claude.start()
        
        # Give Claude a 5s head start to write the plan before Codex wakes up
        time.sleep(5) 
        t_codex.start()

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
- **Claude:** You are the **NAVIGATOR**. Analyze the task, check `SKILLS.md`, and write a technical plan here.
- **Codex:** You are the **DRIVER**. Read Claude's plan and implement the code. Do not hallucinate requirements.

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

    def _agent_runner(self, agent_name: str, role: str, task_name: str):
        """Simulates an agent's lifecycle with Role-Specific Prompts."""
        print(f"[ScrumMaster] Summoning {agent_name} as {role}...")
        
        base_context = self.prepare_context(task_name)
        huddle_path_rel = ".brain/HUDDLE.md" # Relative to cwd
        
        # --- ROLE-SPECIFIC PROMPT ENGINEERING ---
        if role == "NAVIGATOR":
            # Claude's Instructions: Plan, Guide, Review.
            prompt = (
                f"ROLE: NAVIGATOR (Architect). TASK: {task_name}.\n"
                f"{base_context}\n\n"
                "INSTRUCTIONS:\n"
                f"1. Analyze the task and architecture.\n"
                f"2. Write a step-by-step implementation plan in `{huddle_path_rel}`.\n"
                "3. Monitor the code files created by the Driver (Codex).\n"
                f"4. If you see bugs, write feedback in `{huddle_path_rel}`."
            )
            cmd_list = ["claude", "--print", prompt]
            
        elif role == "DRIVER":
            # Codex's Instructions: Read Plan, Code, Report.
            prompt = (
                f"ROLE: DRIVER (Builder). TASK: {task_name}.\n"
                f"{base_context}\n\n"
                "INSTRUCTIONS:\n"
                f"1. Read `{huddle_path_rel}` to see the Navigator's plan.\n"
                "2. Implement the requested code files immediately.\n"
                "3. Do not ask clarifying questions; infer from the plan.\n"
                f"4. When done, write 'COMPLETED' to `{huddle_path_rel}`."
            )
            cmd_list = ["codex", "-p", prompt]

        # --- EXECUTION ---
        if ENABLE_REAL_AGENTS:
            self.sm.start_subprocess(agent_name, cmd_list, cwd=self.project_path)
        else:
            # Simulation Mode
            self._run_simulation(agent_name, role)

    def _run_simulation(self, agent_name, role):
        """Mock output for testing."""
        if role == "NAVIGATOR":
            mock_action = (
                f"echo '[{agent_name}] Reading system patterns...'; sleep 2; "
                f"echo '[{agent_name}] Analysis complete. Writing Plan to HUDDLE.md...'; "
                f"echo '\n**Claude (Navigator):** I have outlined the plan. Codex, please start with the backend API.' >> .brain/HUDDLE.md; "
                f"sleep 2; echo '[{agent_name}] Waiting for Driver...'"
            )
        else:
            mock_action = (
                f"sleep 4; echo '[{agent_name}] Reading HUDDLE.md...'; "
                f"echo '[{agent_name}] Plan received. Generating main.py...'; sleep 2; "
                f"echo '[{agent_name}] Generating requirements.txt...'; sleep 2; "
                f"echo '\n**Codex (Driver):** Backend files generated. Ready for review.' >> .brain/HUDDLE.md; "
                f"echo '[{agent_name}] Done.'"
            )
        # Run simulation in the correct folder too
        self.sm.start_subprocess(agent_name, ["bash", "-c", mock_action], cwd=self.project_path)