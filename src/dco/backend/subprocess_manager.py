import subprocess
import threading
from typing import List, Callable, Dict, Optional

class SubprocessManager:
    def __init__(self):
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.log_callbacks: List[Callable[[str, str], None]] = []

    def register_callback(self, callback: Callable[[str, str], None]):
        self.log_callbacks.append(callback)

    def start_subprocess(self, name: str, command: List[str], cwd: Optional[str] = None):
        """Starts a subprocess in a specific directory."""
        print(f"[SubprocessManager] Starting {name} in {cwd or '.'} with: {' '.join(command)}")
        
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=cwd
            )
            
            self.active_processes[name] = process
            
            # Start monitoring thread
            monitor_thread = threading.Thread(
                target=self._monitor_output,
                args=(name, process),
                daemon=True
            )
            monitor_thread.start()
            return True
        except Exception as e:
            self._broadcast_log(name, f"Failed to start process: {e}")
            return False

    def wait_for_process(self, name: str):
        """Blocks until the specified process finishes."""
        if name in self.active_processes:
            self.active_processes[name].wait()
            # Clean up is handled by _monitor_output, but we wait here.

    def _monitor_output(self, name: str, process: subprocess.Popen):
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
        for callback in self.log_callbacks:
            try:
                callback(name, message)
            except Exception as e:
                print(f"Error in callback: {e}")