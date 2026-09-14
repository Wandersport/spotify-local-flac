import os
import subprocess
import unittest

class TestUISorting(unittest.TestCase):
    """Test suite verifying UI table sorting semantics and queue order."""

    def test_table_sorting_node_suite(self):
        script_path = os.path.join(os.path.dirname(__file__), "test_table_sorting.js")
        self.assertTrue(os.path.exists(script_path), "test_table_sorting.js must exist")
        
        proc = subprocess.run(
            ["node", script_path],
            capture_output=True,
            text=True
        )
        self.assertEqual(
            proc.returncode, 0,
            f"test_table_sorting.js failed with exit code {proc.returncode}:\n{proc.stdout}\n{proc.stderr}"
        )
        self.assertIn("All 9 table sorting unit tests passed successfully!", proc.stdout)

if __name__ == "__main__":
    unittest.main()
