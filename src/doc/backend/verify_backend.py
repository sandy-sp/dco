import sys
import os
import time
import threading

# Add current dir to path to allow imports
sys.path.append(os.getcwd())

def test_imports():
    print("Testing imports...")
    try:
        from backend.memory import MemoryCore
        from backend.scrum import ScrumMaster
        from backend.subprocess_manager import SubprocessManager
        from backend.main import app
        print("Imports successful.")
    except ImportError as e:
        print(f"Import failed: {e}")
        sys.exit(1)

def test_subprocess_manager():
    print("\nTesting SubprocessManager...")
    from backend.subprocess_manager import SubprocessManager
    
    sm = SubprocessManager()
    
    captured_logs = []
    def callback(agent, msg):
        print(f"Callback received: [{agent}] {msg}")
        captured_logs.append(msg)
    
    sm.register_callback(callback)
    
    # Run a simple echo
    sm.start_subprocess("test_agent", ["echo", "Hello World"])
    
    # Give it a moment
    time.sleep(1)
    
    if "Hello World" in captured_logs:
        print("SubprocessManager verified: Captured output.")
    else:
        print("SubprocessManager failed: Did not capture 'Hello World'.")
        print(f"Captured: {captured_logs}")
        sys.exit(1)

if __name__ == "__main__":
    test_imports()
    test_subprocess_manager()
    print("\nBackend verification complete.")
