#!/usr/bin/env python3
"""Run Project Ember — tracking server + watchdog + Streamlit dashboard."""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path

TRACKING_PORT = int(os.environ.get("EMBER_TRACKING_PORT", "8765"))
ALERTS_LOG = os.environ.get("EMBER_ALERTS_LOG", "alerts.log")
OUTPUT_DIR = os.environ.get("EMBER_OUTPUT_DIR", "./honeytokens")
STREAMLIT_PORT = int(os.environ.get("EMBER_STREAMLIT_PORT", "8501"))
WATCHDOG_PORT = int(os.environ.get("EMBER_WATCHDOG_PORT", "8767"))

# Pass these to subprocesses so they stay in sync
EMBERT_ENV = os.environ.copy()
EMBERT_ENV["EMBER_TRACKING_PORT"] = str(TRACKING_PORT)
EMBERT_ENV["EMBER_ALERTS_LOG"] = ALERTS_LOG
EMBERT_ENV["EMBER_OUTPUT_DIR"] = OUTPUT_DIR

TRACKING_SERVER_CODE = fr"""
import os, sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ALERTS_LOG = {repr(ALERTS_LOG)}
TRACKING_PORT = {TRACKING_PORT}
PIXEL_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00"
    b"\xff\xff\xff\x00\x00\x00"
    b"!\xf9\x04\x00\x00\x00\x00\x00"
    b",\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)

class TrackingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.rstrip("/") == "/track":
            params = parse_qs(parsed.query)
            filename = params.get("file", ["unknown"])[0]
            ts = datetime.now().isoformat()
            ip = self.client_address[0]
            ua = self.headers.get("User-Agent", "unknown")
            os.makedirs(os.path.dirname(ALERTS_LOG) or ".", exist_ok=True)
            with open(ALERTS_LOG, "a") as f:
                f.write(f"{{ts}}|TRACK|{{filename}}|{{ip}}|{{ua}}\n")
            self.send_response(200)
            self.send_header("Content-Type", "image/gif")
            self.send_header("Content-Length", str(len(PIXEL_GIF)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.end_headers()
            self.wfile.write(PIXEL_GIF)
        else:
            self.send_response(204)
            self.end_headers()
    def log_message(self, fmt, *args):
        pass

server = HTTPServer(("0.0.0.0", TRACKING_PORT), TrackingHandler)
print(f"[tracking] Server on :{{TRACKING_PORT}}  -> {{ALERTS_LOG}}")
server.serve_forever()
"""


def main():
    print("=" * 56)
    print("  🔥 Project Ember — AI HoneyToken Factory")
    print("=" * 56)

    # Ensure directories
    Path(ALERTS_LOG).parent.mkdir(parents=True, exist_ok=True)
    if not os.path.exists(ALERTS_LOG):
        with open(ALERTS_LOG, "w") as f:
            f.write("")
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    procs = []

    # ── 1. Tracking pixel server ────────────────────────────────────
    print(f"\n[1/3] Tracking pixel server  -> :{TRACKING_PORT}")
    track_proc = subprocess.Popen(
        [sys.executable, "-c", TRACKING_SERVER_CODE],
        stdout=sys.stdout, stderr=sys.stderr, env=EMBERT_ENV,
    )
    procs.append(("tracking", track_proc))
    time.sleep(1)
    if track_proc.poll() is not None:
        print(f"[!] Tracking server failed (exit {track_proc.returncode})")
        sys.exit(1)
    print(f"      http://localhost:{TRACKING_PORT}/track?file=TEST")

    # ── 2. Watchdog daemon ──────────────────────────────────────────
    watchdog_script = str(Path(__file__).parent / "watchdog_daemon.py")
    print(f"\n[2/3] Watchdog daemon        -> {OUTPUT_DIR}")
    watch_proc = subprocess.Popen(
        [sys.executable, watchdog_script, OUTPUT_DIR],
        stdout=sys.stdout, stderr=sys.stderr, env=EMBERT_ENV,
    )
    procs.append(("watchdog", watch_proc))
    time.sleep(1)
    if watch_proc.poll() is not None:
        print(f"      [!] Watchdog exited ({watch_proc.returncode}) — continuing anyway")
    else:
        print(f"      Monitoring {OUTPUT_DIR}/ for changes")

    # ── 3. Streamlit dashboard ──────────────────────────────────────
    print(f"\n[3/3] Streamlit dashboard     -> :{STREAMLIT_PORT}")
    streamlit_args = [
        sys.executable, "-m", "streamlit", "run",
        str(Path(__file__).parent / "app.py"),
        "--server.headless", "true",
        "--server.port", str(STREAMLIT_PORT),
    ]
    streamlit_proc = subprocess.Popen(
        streamlit_args, stdout=sys.stdout, stderr=sys.stderr, env=EMBERT_ENV,
    )
    procs.append(("streamlit", streamlit_proc))

    print(f"\n{'─' * 56}")
    print(f"  🌐 Dashboard  → http://localhost:{STREAMLIT_PORT}")
    print(f"  📡 Tracking   → http://localhost:{TRACKING_PORT}/track?file=NAME")
    print(f"  📁 Monitor    → {OUTPUT_DIR}/")
    print(f"  📋 Alerts     → {ALERTS_LOG}")
    print(f"{'─' * 56}")
    print("  Press Ctrl+C to stop everything\n")

    # ── Shutdown handler ────────────────────────────────────────────
    def shutdown(signum=None, frame=None):
        print("\n[!] Shutting down all services ...")
        for name, proc in reversed(procs):
            if proc.poll() is None:
                proc.terminate()
        for name, proc in reversed(procs):
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("[✓] All stopped.")
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        streamlit_proc.wait()
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
