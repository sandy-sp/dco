import subprocess
import threading
from typing import List, Callable, Dict, Optional

class SubprocessManager:
    def __init__(self):
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.log_callbacks: List[Callable[[str, str], None]] = []

    def register_callback(self, callback: Callable[[str, str], None]):
        self.log_callbacks.append(callback)

    def start_subprocess(self, name: str, command: List[str], cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None):
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
                cwd=cwd,
                env=env
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

    def wait_for_process(self, name: str, timeout: Optional[int] = None) -> bool:
        """Blocks until the specified process finishes. Returns False if timed out."""
        if name in self.active_processes:
            try:
                self.active_processes[name].wait(timeout=timeout)
                return True
            except subprocess.TimeoutExpired:
                return False
        return True

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

    def kill_all(self):
        """Terminates all active processes."""
        for name, process in list(self.active_processes.items()):
            try:
                print(f"[SubprocessManager] Killing {name}...")
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
            except Exception as e:
                print(f"[SubprocessManager] Failed to kill {name}: {e}")
        self.active_processes.clear()

    def _broadcast_log(self, name: str, message: str):
        for callback in self.log_callbacks:
            try:
                callback(name, message)
            except Exception as e:
                print(f"Error in callback: {e}")