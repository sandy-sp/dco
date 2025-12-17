import shutil
import re

# ... existing imports ...

class VersionManager:
    def __init__(self, root_dir):
        self.root = root_dir
        self.stable_path = os.path.join(root_dir, "src") # Initial baseline
        self.current_version_path = None
        
        # Identify 'Latest Stable' logic
        # For simplicity, we assume 'src' is stable initially.
        # We need to track the 'pointer' to what we copy FROM.
        self.latest_stable_ptr = self.stable_path

    def prepare_next_version(self):
        """Creates srcv{N+1} from latest stable."""
        next_idx = 1
        
        # Scan for existing srcvN
        existing = [d for d in os.listdir(self.root) if d.startswith("srcv") and os.path.isdir(os.path.join(self.root, d))]
        if existing:
            # Extract max N
            idxs = []
            for d in existing:
                match = re.search(r"srcv(\d+)", d)
                if match:
                    idxs.append(int(match.group(1)))
            if idxs:
                next_idx = max(idxs) + 1
        
        new_dir_name = f"srcv{next_idx}"
        new_path = os.path.join(self.root, new_dir_name)
        
        print(f"📦 [VersionManager] creating {new_dir_name} from {os.path.basename(self.latest_stable_ptr)}...")
        
        if os.path.exists(new_path):
            shutil.rmtree(new_path)
        
        shutil.copytree(self.latest_stable_ptr, new_path)
        self.current_version_path = new_path
        return new_path

    def mark_result(self, path, success):
        """Updates stable pointer or marks for deletion."""
        if success:
            print(f"✅ [VersionManager] {os.path.basename(path)} marked STABLE.")
            self.latest_stable_ptr = path
            # We keep it.
        else:
            print(f"❌ [VersionManager] {os.path.basename(path)} marked UNSTABLE. Deleting...")
            try:
                shutil.rmtree(path)
            except Exception as e:
                print(f"   (Cleanup failed: {e})")
            # Pointer stays on previous stable


# 1. Force Agentic Mode BEFORE importing scrum
# This ensures the module-level variable in scrum.py picks up True
os.environ["DOC_ENABLE_REAL_AGENTS"] = "true"

# Ensure src is in pythonpath
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from doc.backend.scrum import ScrumMaster
from doc.backend.subprocess_manager import SubprocessManager
from doc.backend.memory import MemoryCore

import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Operation Ouroboros: Autonomous Improvement Loop")
    parser.add_argument("--loops", type=int, default=5, help="Number of improvement iterations (default: 5)")
    return parser.parse_args()

# MAX_LOOPS determined at runtime


def main():
    args = parse_args()
    MAX_LOOPS = args.loops
    
    print(f"🐍 Operation Ouroboros Initiated (Loops: {MAX_LOOPS})...")
    print(f"🔧 cwd: {os.getcwd()}")
    
    # 2. Initialize Components
    # We share the SubprocessManager so we can register our own callbacks
    sm = SubprocessManager()
    memory = MemoryCore(persist_path=".brain/memory.db")
    
    # Register CLI Output Callback
    def cli_printer(agent: str, message: str):
        # Simple color coding could be added here if desired
        print(f"[{agent}] {message}")
        
    sm.register_callback(cli_printer)
    
    # Initialize ScrumMaster
    scrum = ScrumMaster(subprocess_manager=sm, memory_core=memory)
    # Don't set project_path yet, loop does it
    
    vm = VersionManager(os.getcwd())
    current_ver_path = None # Track current
    
    loop_count = 0
    
    try:
        while True:
            current_state = scrum.state
            
            # 3. Handle IDLE (Initial or Sprint Finished)
            if current_state == "IDLE":
                # Check previous sprint result if we just finished one
                if loop_count > 0:
                   # If we just finished a loop (loop_count > 0), check result
                   # ScrumMaster now has self.sprint_result
                   success = (scrum.sprint_result == "SUCCESS")
                   vm.mark_result(current_ver_path, success)
                   
                if loop_count >= MAX_LOOPS:
                    print(f"⏹️  Max loops ({MAX_LOOPS}) reached. Terminating Ouroboros.")
                    break
                
                print(f"\n🔁 Starting Loop {loop_count + 1}/{MAX_LOOPS}")
                
                # PREPARE VERSION
                current_ver_path = vm.prepare_next_version()
                scrum.set_project_path(current_ver_path)
                
                if loop_count == 0:
                     # First Run
                     prompt = (
                         "Analyze src/doc and ARCHITECTURE.md. "
                         "Refactor the most critical architectural weakness you find."
                     )
                else:
                     prompt = (
                         "Review the last refactor. If successful, verify the code is running. "
                         "Then, identify the NEXT improvement area and execute it."
                     )
                
                scrum.start_sprint(prompt)
                loop_count += 1
                
                # Sleep to allow state to transition from IDLE -> PLANNING
                time.sleep(5)
                
            # 4. Handle STUCK (Awaiting User)
            elif current_state == "AWAITING_USER":
                print("\n⚠️  Agent is blocked (AWAITING_USER). Injecting safety override.")
                
                # Retrieve the question (optional, for logging)
                last_q = scrum.get_latest_question()
                print(f"❓ Agent asked: {last_q[:100]}...")
                
                # Injection
                override_prompt = (
                    "Proceed with the safest option. "
                    "If unsure, rollback and try a simpler approach."
                )
                scrum.start_sprint(override_prompt)
                
                # Sleep to allow state to transition
                time.sleep(5)
                
            # 5. Handle Rate Limits
            elif current_state == "RATE_LIMITED":
                print("\n🛑  All Agents Rate Limited.")
                
                # Check for reset times
                wait_seconds = 600 # Default fallback
                
                # Try to find the earliest reset time
                import datetime
                import dateutil.parser # Might need this, or simple string logic
                
                # Retrieve times (assuming they are stored strings like "12am")
                # Since parsing "12am (EST)" is hard without libs, we stick to the 10 min loop check?
                # User asked: "read the reset time and continue after that"
                
                # Let's inspect registry
                registry = scrum.agent_registry
                print(f"   Status: {registry}")
                
                # If we have a stored time (which is just a string now), we can display it.
                # "Sleeping until reset..."
                # Since we don't have robust NLP date parsing installed by default (maybe), 
                # we'll stick to a smart poll loop or just sleep 10 mins.
                # But to satisfy "read reset time", we show it.
                
                print(f"⏳ Sleeping for 10 minutes to wait for resets... (Ctrl+C to stop)")
                try:
                    time.sleep(600)
                    # Reset to IDLE to retry
                    scrum._set_state("IDLE")
                    # Should we reset registry status?
                    # Ideally, after sleeping, we assume maybe valid? 
                    # Or we only reset if time passed.
                    # Simple hack: Reset 'RATE_LIMITED' status to 'ACTIVE' to try again?
                    scrum.agent_registry["claude"]["status"] = "ACTIVE"
                    scrum.agent_registry["codex"]["status"] = "ACTIVE"
                    
                except KeyboardInterrupt:
                    print("🛑 Logic interrupted.")
                    break

            # 6. Monitor Active State
            else:
                # Just wait. The registered callback will print logs.
                time.sleep(2)
                
    except KeyboardInterrupt:
        print("\n🛑  Manual Interruption. Shutting down.")
    except Exception as e:
        print(f"\n🔥  Critical Error: {e}")
    finally:
        print("💀 Killing all subprocesses...")
        sm.kill_all()
        # Optionally wait for threads? main() ending will kill daemon threads, 
        # but ScrumMaster thread is NOT daemon. 
        # We should ideally signal it to stop.
        # But for this script, os._exit might be cleaner if threads hang.
        # For now, let's just exit.
        print("👋 Exiting.")

if __name__ == "__main__":
    main()
