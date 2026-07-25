#!/usr/bin/env python3
"""Run Ember Forest AI — Streamlit dashboard for multi-modal forest intelligence."""

import os
import sys
import subprocess
from pathlib import Path

STREAMLIT_PORT = int(os.environ.get("EMBER_FOREST_PORT", "8501"))

print("=" * 56)
print("  🌳 Ember Forest AI — Forest Intelligence Platform")
print("=" * 56)
print()
print("  Upload a tree photo, forest audio recording, or land")
print("  description. Gemini 2.0 Flash analyzes everything.")
print()
print(f"  Dashboard → http://localhost:{STREAMLIT_PORT}")
print()

args = [
    sys.executable, "-m", "streamlit", "run",
    str(Path(__file__).parent / "forest_app.py"),
    "--server.headless", "true",
    "--server.port", str(STREAMLIT_PORT),
    "--server.address", "0.0.0.0",
]

try:
    proc = subprocess.Popen(args, stdout=sys.stdout, stderr=sys.stderr)
    proc.wait()
except KeyboardInterrupt:
    proc.terminate()
    proc.wait()
    print("\n[✓] Stopped.")
