"""Tests for --debug CLI flag and LOG_LEVEL environment variable handling."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.config import Config


class TestDebugFlag(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "config.json")
        self.orig_log_level = os.environ.get("LOG_LEVEL")

    def tearDown(self):
        if self.orig_log_level is not None:
            os.environ["LOG_LEVEL"] = self.orig_log_level
        else:
            os.environ.pop("LOG_LEVEL", None)
        shutil.rmtree(self.temp_dir)

    def test_default_log_level_is_info(self):
        os.environ.pop("LOG_LEVEL", None)
        cfg = Config(self.config_path)
        self.assertEqual(cfg.log_level, "INFO")

    def test_env_var_log_level_overrides_config(self):
        os.environ["LOG_LEVEL"] = "DEBUG"
        cfg = Config(self.config_path)
        self.assertEqual(cfg.log_level, "DEBUG")

        os.environ["LOG_LEVEL"] = "warning"
        self.assertEqual(cfg.log_level, "WARNING")

    def test_config_file_log_level_used_when_env_not_set(self):
        os.environ.pop("LOG_LEVEL", None)
        cfg = Config(self.config_path)
        cfg.data["log_level"] = "ERROR"
        self.assertEqual(cfg.log_level, "ERROR")


if __name__ == "__main__":
    unittest.main()
