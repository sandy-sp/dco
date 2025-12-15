import subprocess
import threading
import asyncio
from typing import List, Callable, Dict

class SubprocessManager:
    def __init__(self):
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.log_callbacks: List[Callable[[str, str], None]] = []

    def register_callback(self, callback: Callable[[str, str], None]):
        """Registers a callback to receive logs (agent_name, log_line)."""
        self.log_callbacks.append(callback)

    def start_subprocess(self, name: str, command: List[str]):
        """Starts a subprocess and spawns a thread to monitor stdout."""
        print(f"[SubprocessManager] Starting {name} with command: {' '.join(command)}")
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )
        
        self.active_processes[name] = process
        
        # Start monitoring thread
        monitor_thread = threading.Thread(
            target=self._monitor_output,
            args=(name, process),
            daemon=True
        )
        monitor_thread.start()

    def _monitor_output(self, name: str, process: subprocess.Popen):
        """Reads stdout line by line and triggers callbacks."""
        try:
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                stripped = line.rstrip()
                if stripped:
                     self._broadcast_log(name, stripped)
        except Exception as e:
            self._broadcast_log(name, f"Error reading stream: {e}")
        finally:
            process.stdout.close()
            process.wait()
            self._broadcast_log(name, "Process terminated.")
            if name in self.active_processes:
                del self.active_processes[name]

    def _broadcast_log(self, name: str, message: str):
        """Invokes all registered callbacks."""
        for callback in self.log_callbacks:
            try:
                callback(name, message)
            except Exception as e:
                print(f"Error in callback: {e}")
