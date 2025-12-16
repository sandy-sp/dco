import time
import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from backend.subprocess_manager import SubprocessManager
from backend.scrum import ScrumMaster
from backend.memory import MemoryCore

console = Console()

def main():
    console.clear()
    console.print(Panel.fit("[bold blue]DCO: Dual-Core Orchestrator[/bold blue]\n[dim]Twin-Turbo Terminal Edition[/dim]"))

    # Setup Backend
    sm = SubprocessManager()
    mem = MemoryCore()
    
    # We pass a dummy broadcast func since we are in CLI mode
    scrum = ScrumMaster(sm, mem, broadcast_func=None) 
    
    # 1. Project Setup
    project_path = console.input("[bold yellow]Enter Project Path (default: .): [/bold yellow]") or "."
    scrum.set_project_path(project_path)

    # 2. Main Input Loop
    while True:
        task = console.input("\n[bold green]Mission Instruction > [/bold green]")
        if task.lower() in ['exit', 'quit']:
            break

        # Register a callback to print logs to terminal in real-time
        def cli_logger(agent, msg):
            color = "blue" if agent == "claude" else "green"
            console.print(f"[{color}][{agent.upper()}][/{color}] {msg}")

        sm.register_callback(cli_logger)

        console.print(f"[bold]🚀 Starting Mission: {task}[/bold]")
        scrum.start_sprint(task)

        # Wait loop (Keep CLI alive while agents work)
        while scrum.state != "IDLE" and scrum.state != "AWAITING_USER":
            time.sleep(0.5)

        if scrum.state == "AWAITING_USER":
            console.print("[bold red]⚠️ Agents requested input![/bold red]")
            # Loop restarts, allowing user to reply

if __name__ == "__main__":
    main()