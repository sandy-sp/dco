import threading
import time

class ScrumMaster:
    def __init__(self, subprocess_manager):
        self.sm = subprocess_manager
        self.state = "IDLE"

    def start_sprint(self, task_name: str):
        """Initiates the Twin-Turbo workflow by spinning up agents."""
        if self.state != "IDLE":
             print(f"[ScrumMaster] Cannot start sprint. Current state: {self.state}")
             return

        print(f"[ScrumMaster] Starting Sprint: {task_name}")
        self.state = "SPRINTING"

        # Spin up threads for agents
        t_claude = threading.Thread(target=self._agent_runner, args=("claude",))
        t_codex = threading.Thread(target=self._agent_runner, args=("codex",))
        
        t_claude.start()
        t_codex.start()

    def _agent_runner(self, agent_name: str):
        """Simulates an agent's lifecycle."""
        print(f"[ScrumMaster] Summoning {agent_name}...")
        
        # In a real scenario, this would call actual CLI commands.
        # For now, we use the subprocess manager to run a dummy command
        # that mimics agent activity (writing to stdout).
        
        # Using a long-running echo to simulate work
        cmd = f"echo '[{agent_name}] Analysis started...'; sleep 2; echo '[{agent_name}] Writing code...'; sleep 2; echo '[{agent_name}] Done.'"
        
        self.sm.start_subprocess(agent_name, ["bash", "-c", cmd])
        
        # After process finishes, we could trigger validaton, etc.
        # But since start_subprocess is async (managed by manager), 
        # we strictly just kickoff here.
