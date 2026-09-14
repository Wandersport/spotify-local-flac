import unittest
import subprocess
import os

class TestFolderNavigation(unittest.TestCase):
    def test_live_folder_navigation(self):
        """Run the automated CDP live folder navigation & state regression test."""
        test_file = os.path.join(os.path.dirname(__file__), "test_folder_navigation.js")
        result = subprocess.run(["node", test_file], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, f"Folder navigation regression test failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")

if __name__ == "__main__":
    unittest.main()
