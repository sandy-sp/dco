import threading
import time
import os
import datetime
from .memory import MemoryCore

ENABLE_REAL_AGENTS = False  # Set to True to enable actual CLI execution

class ScrumMaster:
    def __init__(self, subprocess_manager, memory_core: MemoryCore):
        self.sm = subprocess_manager
        self.memory = memory_core
        self.state = "IDLE"

    def start_sprint(self, task_name: str):
        """Initiates the Twin-Turbo workflow by spinning up agents."""
        if self.state != "IDLE":
             print(f"[ScrumMaster] Cannot start sprint. Current state: {self.state}")
             return

        print(f"[ScrumMaster] Starting Sprint: {task_name}")
        self.state = "SPRINTING"
        
        # 1. Initialize Huddle
        self.initialize_huddle(task_name)

        # 2. Spin up threads for agents
        t_claude = threading.Thread(target=self._agent_runner, args=("claude", task_name))
        t_codex = threading.Thread(target=self._agent_runner, args=("codex", task_name))
        
        t_claude.start()
        t_codex.start()

    def initialize_huddle(self, task_name: str):
        """Resets the HUDDLE.md file."""
        header = f"# New Sprint: {task_name}\n\n**Orchestrator ({datetime.datetime.now().isoformat()}):** Agents, please align on the plan.\n"
        try:
            with open(".brain/HUDDLE.md", "w", encoding="utf-8") as f:
                f.write(header)
            print("[ScrumMaster] Huddle initialized.")
        except Exception as e:
            print(f"[ScrumMaster] Failed to init huddle: {e}")

    def prepare_context(self, task_name: str) -> str:
        """Constructs the context prompt for agents."""
        # Read System Patterns
        patterns = ""
        try:
            with open(".brain/context/systemPatterns.md", "r", encoding="utf-8") as f:
                patterns = f.read()
        except FileNotFoundError:
            patterns = "No system patterns found."

        # Query Memory (Skills)
        # Using a collection named 'skills' for lessons learned
        mem_results = self.memory.query_memory("skills", task_name)
        skills = ""
        if mem_results and mem_results['documents'] and mem_results['documents'][0]:
            skills = "\n".join(mem_results['documents'][0])
        
        context = f"""
Task: {task_name}
System Patterns:
{patterns}

Relevant Skills/Lessons:
{skills if skills else "None"}
"""
        return context

    def _agent_runner(self, agent_name: str, task_name: str):
        """Simulates an agent's lifecycle."""
        print(f"[ScrumMaster] Summoning {agent_name}...")
        
        # Prepare Context
        context = self.prepare_context(task_name)
        
        # Construct Command
        cmd_list = []
        if agent_name == "claude":
            prompt = f"{context}\n\nRead .brain/HUDDLE.md. Output your plan."
            cmd_list = ["claude", "--print", prompt]
        elif agent_name == "codex":
            prompt = f"{context}\n\nRead .brain/HUDDLE.md. Implement the agreed plan."
            cmd_list = ["codex", "-p", prompt]
            
        cmd_str = " ".join(cmd_list)
        
        if ENABLE_REAL_AGENTS:
            self.sm.start_subprocess(agent_name, cmd_list)
        else:
            # Simulation Mode
            simulation_msg = f"[SIMULATION] Would run: {cmd_str}"
            # We use a delayed echo so the user can see it "happening"
            mock_cmd = f"echo '{simulation_msg}'; sleep 2; echo '[{agent_name}] working...'; sleep 2; echo '[{agent_name}] done.'"
            self.sm.start_subprocess(agent_name, ["bash", "-c", mock_cmd])
