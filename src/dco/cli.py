import time
import os
import sys
from rich.console import Console
from rich.panel import Panel
from dco.backend.subprocess_manager import SubprocessManager
from dco.backend.scrum import ScrumMaster
from dco.backend.memory import MemoryCore

console = Console()

def main():
    console.clear()
    console.print(Panel.fit("[bold blue]DCO: Dual-Core Orchestrator[/bold blue]\n[dim]Twin-Turbo Terminal Edition[/dim]"))

    sm = SubprocessManager()
    mem = MemoryCore()
    scrum = ScrumMaster(sm, mem, broadcast_func=None)
    
    # 1. Project Setup
    default_path = os.getcwd()
    project_path = console.input(f"[bold yellow]Enter Project Path (default: {default_path}): [/bold yellow]") or default_path
    scrum.set_project_path(project_path)

    # 2. Main Input Loop
    while True:
        # --- DYNAMIC PROMPT LOGIC ---
        if scrum.state == "AWAITING_USER":
            # Fetch what the agents asked
            last_msg = scrum.get_latest_question()
            console.print(f"\n[bold red]🤖 Agents Need Input:[/bold red]")
            console.print(Panel(last_msg, border_style="red"))
            prompt_text = "\n[bold yellow]Reply to Agents > [/bold yellow]"
        else:
            prompt_text = "\n[bold green]Mission Instruction > [/bold green]"

        # Wait for user input
        try:
            user_input = console.input(prompt_text)
        except KeyboardInterrupt:
            console.print("\n[dim]Exiting...[/dim]")
            break

        if user_input.lower() in ['exit', 'quit']:
            break

        # Register logger only once
        if not sm.log_callbacks:
            def cli_logger(agent, msg):
                color = "blue" if agent == "claude" else "green"
                console.print(f"[{color}][{agent.upper()}][/{color}] {msg}")
            sm.register_callback(cli_logger)

        scrum.start_sprint(user_input)

        # Wait loop (Keep CLI alive while agents work)
        try:
            while scrum.state != "IDLE" and scrum.state != "AWAITING_USER":
                time.sleep(0.5)
        except KeyboardInterrupt:
            console.print("\n[bold red]🛑 Mission Interrupted![/bold red]")
            # Ideally add logic to kill subprocesses here
            break

if __name__ == "__main__":
    main()