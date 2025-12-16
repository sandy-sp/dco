import time
import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.markdown import Markdown
from rich.text import Text
from rich.box import ROUNDED

from doc.backend.subprocess_manager import SubprocessManager
from doc.backend.scrum import ScrumMaster, ENABLE_REAL_AGENTS, CLAUDE_BIN, CODEX_BIN
from doc.backend.memory import MemoryCore

console = Console()

# --- TUI HELPERS ---

def make_layout() -> Layout:
    """Defines the TUI grid structure."""
    layout = Layout()
    
    # Split into Header (Top), Main (Middle), Footer (Bottom)
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
    )
    
    # Split Main into Huddle (Left/Top) and Logs (Right/Bottom)
    # Using a vertical split for better readability of chat
    layout["main"].split(
        Layout(name="huddle", ratio=2),
        Layout(name="logs", ratio=1),
    )
    
    return layout

def get_huddle_content(memory: MemoryCore) -> Markdown:
    """Reads the tail of the interaction log from Memory."""
    try:
        content = memory.get_recent_huddle(limit=20)
        if not content.strip():
             return Markdown("*Huddle is empty / System Ready*")
        return Markdown(content)
    except Exception as e:
        return Markdown(f"*Error reading Memory: {e}*")

class LogBuffer:
    """Simple buffer to hold recent logs for display."""
    def __init__(self, size=10):
        self.size = size
        self.logs = []

    def append(self, agent, msg):
        color = "blue" if agent == "claude" else "green"
        self.logs.append(f"[{color}][{agent.upper()}][/{color}] {msg}")
        if len(self.logs) > self.size:
            self.logs.pop(0)

    def get_renderable(self):
        return Text.from_markup("\n".join(self.logs))

def handle_command(user_input: str, scrum: ScrumMaster, console: Console):
    """Handles commands starting with /."""
    if not user_input.startswith("/"):
        return False

    cmd = user_input.split(" ")[0].lower()
    
    if cmd == "/clear":
        scrum.memory.clear_huddle()
        scrum.state = "IDLE"
        # log_buffer.append("SYSTEM", "Memory cleared and state reset.") # Removed to match signature
        console.print("[bold cyan][SYSTEM] Memory cleared.[/bold cyan]")
        
    elif cmd == "/map":
        map_path = os.path.join(scrum.project_path, ".brain/repo_map.txt")
        if os.path.exists(map_path):
            with open(map_path, "r") as f:
                console.print(Panel(f.read(), title="Repo Map", border_style="blue", box=ROUNDED))
        else:
            console.print("[bold red]Repo Map not found. Run a mission first.[/bold red]")
    
    elif cmd == "/config":
        config_info = (
            f"Project Path: {scrum.project_path}\n"
            f"Real Agents Enabled: {ENABLE_REAL_AGENTS}\n"
            f"Current State: {scrum.state}"
        )
        console.print(Panel(config_info, title="Configuration", border_style="magenta", box=ROUNDED))
        
    elif cmd == "/help":
        help_text = (
            "/clear  - Wipe Huddle Memory and reset state\n"
            "/map    - Print repo map\n"
            "/mode   - Toggle Simulation / Real Agents\n"
            "/status - Show active repo and agents\n"
            "/config - Show configuration\n"
            "/help   - Show this help"
        )
        console.print(Panel(help_text, title="Available Commands", border_style="white", box=ROUNDED))
    
    elif cmd == "/mode":
        # Toggle Sim/Real
        import doc.backend.scrum as scrum_module
        current = scrum_module.ENABLE_REAL_AGENTS
        scrum_module.ENABLE_REAL_AGENTS = not current
        state = "REAL AGENTS" if scrum_module.ENABLE_REAL_AGENTS else "SIMULATION"
        console.print(f"[bold yellow]Runtime Mode Switched to: {state}[/bold yellow]")
        
    elif cmd == "/status":
        import doc.backend.scrum as scrum_module
        mode = "REAL AGENTS" if scrum_module.ENABLE_REAL_AGENTS else "SIMULATION"
        status_info = (
            f"Project: [bold cyan]{scrum.project_path}[/bold cyan]\n"
            f"Mode:    [bold yellow]{mode}[/bold yellow]\n"
            f"Agents:  Claude='{scrum_module.CLAUDE_BIN}', Codex='{scrum_module.CODEX_BIN}'\n"
            f"State:   {scrum.state}"
        )
        console.print(Panel(status_info, title="System Status", border_style="blue", box=ROUNDED))
        
    else:
        console.print(f"[bold red]Unknown command: {user_input}[/bold red]")
        
    return True

# --- MAIN ---

def main():
    console.clear()
    
    sm = SubprocessManager()
    mem = MemoryCore()
    scrum = ScrumMaster(sm, mem, broadcast_func=None)
    log_buffer = LogBuffer(size=8)

    # 1. Project Setup
    console.print(Panel.fit("[bold blue]DOC: Dual Orchestrator Core[/bold blue]\n[dim]Twin-Turbo Terminal Edition[/dim]", box=ROUNDED))
    default_path = os.getcwd()
    project_path = console.input(f"[bold yellow]Enter Project Path (default: {default_path}): [/bold yellow]") or default_path
    scrum.set_project_path(project_path)
    
    # Register Logger
    def cli_logger(agent, msg):
        log_buffer.append(agent, msg)
    sm.register_callback(cli_logger)

    # 2. Main Input Loop
    try:
        while True:
            # --- DYNAMIC PROMPT LOGIC ---
            if scrum.state == "AWAITING_USER":
                last_msg = scrum.get_latest_question()
                console.print(f"\n[bold red]🤖 Agents Need Input:[/bold red]")
                console.print(Panel(last_msg, border_style="red", box=ROUNDED))
                prompt_text = "[bold yellow]Reply to Agents > [/bold yellow]"
            else:
                prompt_text = "\n[bold green]Mission Instruction > [/bold green]"

            try:
                user_input = console.input(prompt_text)
            except KeyboardInterrupt:
                break

            if user_input.lower() in ['exit', 'quit']:
                break
                
            if handle_command(user_input, scrum, console):
                continue

            # Start Sprint
            scrum.start_sprint(user_input)

            # --- LIVE TUI MODE ---
            # Activate the Live Display while agents are working
            layout = make_layout()
            layout["header"].update(Panel(f"Mission: {user_input}", style="bold white on blue", box=ROUNDED))
            
            with Live(layout, refresh_per_second=4, screen=False):
                while scrum.state != "IDLE" and scrum.state != "AWAITING_USER":
                    
                    # Update Huddle View
                    huddle_md = get_huddle_content(scrum.memory)
                    layout["huddle"].update(Panel(huddle_md, title="📣 The Huddle", border_style="cyan", box=ROUNDED))
                    
                    # Update Logs View
                    layout["logs"].update(Panel(log_buffer.get_renderable(), title="🖥️  System Logs", border_style="dim", box=ROUNDED))
                    
                    time.sleep(0.25)

            # Loop cleanup
            if scrum.state == "AWAITING_USER":
                # The loop in main() will hit the "AWAITING_USER" block at top
                pass
            else:
                console.print("[bold green]Mission Completed.[/bold green]")
    finally:
        sm.kill_all()
        console.print("[dim]Backend processes terminated.[/dim]")

if __name__ == "__main__":
    main()