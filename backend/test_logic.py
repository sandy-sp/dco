import unittest
import os
import shutil
from backend.scrum import ScrumMaster
from backend.memory import MemoryCore
from backend.subprocess_manager import SubprocessManager

class TestScrumMaster(unittest.TestCase):
    def setUp(self):
        # Setup temp brain
        self.test_brain = ".test_brain"
        os.makedirs(os.path.join(self.test_brain, "context"), exist_ok=True)
        
        # Create dummy system patterns
        with open(os.path.join(self.test_brain, "context", "systemPatterns.md"), "w") as f:
            f.write("TEST PATTERN: Always be cool.")

        # Init components
        # We subclass to override paths for testing if needed, or just monkeypatch paths
        self.sm = SubprocessManager()
        self.mem = MemoryCore(persist_path=os.path.join(self.test_brain, "memory.db"))
        self.scrum = ScrumMaster(self.sm, self.mem)
        
        # Monkeypatch file paths in ScrumMaster for testing directory
        # This is a bit hacky but avoids changing the prod code to accept config for paths for this MVP.
        # Ideally, we'd pass config.
        # For now, let's just use the relative paths and cleanup.
        # ACTUALLY, to avoid messing with real .brain, let's swap the directory temporarily.
        if os.path.exists(".brain"):
            os.rename(".brain", ".brain_backup")
        os.rename(self.test_brain, ".brain")

    def tearDown(self):
        # Restore
        if os.path.exists(".brain"):
            shutil.rmtree(".brain")
        if os.path.exists(".brain_backup"):
            os.rename(".brain_backup", ".brain")

    def test_prepare_context(self):
        context = self.scrum.prepare_context("Build a spaceship")
        self.assertIn("Task: Build a spaceship", context)
        self.assertIn("TEST PATTERN: Always be cool.", context)
        print("\n[Test] Context generation verified.")

    def test_initialize_huddle(self):
        self.scrum.initialize_huddle("Deep Sea Mission")
        with open(".brain/HUDDLE.md", "r") as f:
            content = f.read()
        self.assertIn("# New Sprint: Deep Sea Mission", content)
        print("\n[Test] Huddle initialization verified.")

if __name__ == '__main__':
    unittest.main()
