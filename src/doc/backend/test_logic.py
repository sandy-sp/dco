import unittest
from unittest.mock import MagicMock, patch
import os
import shutil
import doc.backend.scrum as scrum_module
from doc.backend.scrum import ScrumMaster
from doc.backend.memory import MemoryCore
from doc.backend.subprocess_manager import SubprocessManager

class TestScrumMaster(unittest.TestCase):
    def setUp(self):
        # Setup temp brain
        self.test_brain = ".test_brain"
        os.makedirs(os.path.join(self.test_brain, "context"), exist_ok=True)
        # Create dummy system patterns
        with open(os.path.join(self.test_brain, "context", "systemPatterns.md"), "w") as f:
            f.write("TEST PATTERN: Verify logic.")
        
        # Mock SubprocessManager
        self.mock_sm = MagicMock(spec=SubprocessManager)
        
        # Mock MemoryCore
        self.mock_mem = MagicMock(spec=MemoryCore)
        self.mock_mem.query_memory.return_value = {"documents": [["Skill 1"]]}
        
        # Initialize ScrumMaster
        self.scrum = ScrumMaster(self.mock_sm, self.mock_mem)
        self.scrum.set_project_path(os.path.abspath(self.test_brain))

    def tearDown(self):
        if os.path.exists(self.test_brain):
            shutil.rmtree(self.test_brain)

    @patch('doc.backend.scrum.ENABLE_REAL_AGENTS', True)  # Force real command generation
    @patch('time.sleep', return_value=None)          # Skip sleep delays
    @patch('threading.Thread')                       # Mock Threading
    def test_start_sprint_roles(self, mock_thread_cls, mock_sleep):
        """Verify that agents are assigned correct roles and prompts."""
        
        # Setup MockThread to run synchronously
        class MockThread:
            def __init__(self, target, args):
                self.target = target
                self.args = args
            def start(self):
                self.target(*self.args)
        
        mock_thread_cls.side_effect = MockThread

        # Execute Sprint
        task = "Build a Login Form"
        self.scrum.start_sprint(task)

        # Get all calls to start_subprocess
        # We expect 2 calls: one for Claude, one for Codex
        # start_subprocess(name, command, cwd=...)
        
        self.assertEqual(self.mock_sm.start_subprocess.call_count, 2)
        
        calls = self.mock_sm.start_subprocess.call_args_list
        
        # Analyze Calls
        claude_call = None
        codex_call = None
        
        for call in calls:
            args, kwargs = call
            name = args[0]
            cmd = args[1]
            cmd_str = " ".join(cmd)
            
            if name == "claude":
                claude_call = cmd_str
            elif name == "codex":
                codex_call = cmd_str

        # Verify Claude (Navigator)
        self.assertIsNotNone(claude_call, "Claude was not summoned")
        self.assertIn("ROLE: NAVIGATOR", claude_call)
        self.assertIn("Write a step-by-step implementation plan", claude_call)
        print("\n[PASS] Claude assigned NAVIGATOR role.")

        # Verify Codex (Driver)
        self.assertIsNotNone(codex_call, "Codex was not summoned")
        self.assertIn("ROLE: DRIVER", codex_call)
        self.assertIn("Implement the requested code files", codex_call)
        print("[PASS] Codex assigned DRIVER role.")
        
        # Verify Sequencing (Mock Thread runs sync, so order matches definition)
        # We can't strictly prove time delay with sync mock, but we verified sleep was called
        # mock_sleep should be called at least once (the 5s delay)
        mock_sleep.assert_called()
        print("[PASS] Sequencing delay verified (sleep called).")

if __name__ == '__main__':
    unittest.main()
