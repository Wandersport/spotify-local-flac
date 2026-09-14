#!/usr/bin/env python3
"""
scripts/generate_extension.py - Legacy wrapper for scripts/build.py.
"""

from pathlib import Path
import sys

# Forward to scripts/build.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import build

if __name__ == "__main__":
    build()
