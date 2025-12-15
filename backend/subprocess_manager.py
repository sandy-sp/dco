import subprocess
import threading
from typing import List, Callable, Dict, Optional

class SubprocessManager:
    def __init__(self):
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.log_callbacks: List[Callable[[str, str], None]] = []

    def register_callback(self, callback: Callable[[str, str], None]):
        self.log_callbacks.append(callback)

    def start_subprocess(self, name: str, command: List[str], cwd: Optional[str] = None, on_exit: Optional[Callable[[], None]] = None):
        """Starts a subprocess in a specific directory (cwd)."""
        print(f"[SubprocessManager] Starting {name} in {cwd or '.'} with: {' '.join(command)}")
        
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=cwd  # <--- CRITICAL: Execute inside the project folder
            )
            
            self.active_processes[name] = process
            
            monitor_thread = threading.Thread(
                target=self._monitor_output,
                args=(name, process, on_exit),
                daemon=True
            )
            monitor_thread.start()
        except Exception as e:
            self._broadcast_log(name, f"Failed to start process: {e}")
            if on_exit:
                on_exit()

    def _monitor_output(self, name: str, process: subprocess.Popen, on_exit: Optional[Callable[[], None]] = None):
        try:
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                stripped = line.rstrip()
                if stripped:
                     self._broadcast_log(name, stripped)
                     
            process.wait()
            self._broadcast_log(name, f"Process terminated (Exit Code: {process.returncode})")
            
        except Exception as e:
            self._broadcast_log(name, f"Stream error: {e}")
        finally:
            if name in self.active_processes:
                del self.active_processes[name]
            if on_exit:
                try:
                    on_exit()
                except Exception as e:
                    print(f"[SubprocessManager] Error in on_exit callback: {e}")

    def _broadcast_log(self, name: str, message: str):
        for callback in self.log_callbacks:
            try:
                callback(name, message)
            except Exception as e:
                print(f"Error in callback: {e}")