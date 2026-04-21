#!/usr/bin/env python
"""Run E2E test."""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, '-m', 'pytest', 
     'test_e2e.py::TestFigmentE2E::test_playlist_creation', '-v'],
    cwd='.'
)
sys.exit(result.returncode)
