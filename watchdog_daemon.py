import os
import time
import logging
from datetime import datetime
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

ALERTS_LOG = os.environ.get("EMBER_ALERTS_LOG", "alerts.log")

EXCLUDE_DIRS = {"__pycache__", ".git", ".DS_Store"}


class HoneyTokenEventHandler(FileSystemEventHandler):
    def __init__(self, watch_root):
        self.watch_root = os.path.abspath(watch_root)

    def _rel(self, path):
        try:
            return os.path.relpath(path, self.watch_root)
        except ValueError:
            return path

    def _should_ignore(self, path):
        parts = Path(path).parts
        return any(excl in parts for excl in EXCLUDE_DIRS)

    def _log(self, event_type, src_path, details=""):
        if self._should_ignore(src_path):
            return
        rel = self._rel(src_path)
        ts = datetime.now().isoformat()
        line = f"{ts}|{event_type}|{rel}|{details}\n"
        with open(ALERTS_LOG, "a") as f:
            f.write(line)
        print(f"[WATCHDOG] {line.strip()}")

    def on_modified(self, event):
        if event.is_directory:
            return
        if self._should_ignore(event.src_path):
            return
        if event.src_path.endswith(".log"):
            return
        self._log("MODIFIED", event.src_path, "File content changed — possible ransomware encryption")

    def on_created(self, event):
        if event.is_directory:
            return
        if self._should_ignore(event.src_path):
            return
        self._log("CREATED", event.src_path, "New file appeared in monitored directory")

    def on_deleted(self, event):
        if event.is_directory:
            return
        if self._should_ignore(event.src_path):
            return
        self._log("DELETED", event.src_path, "File removed — possible sabotage or cleanup")

    def on_moved(self, event):
        if event.is_directory:
            return
        if self._should_ignore(event.src_path):
            return
        self._log("MOVED", event.src_path, f"File moved/renamed — new location: {event.dest_path}")


def start_monitoring(directory, recursive=True):
    watch_path = os.path.abspath(directory)
    os.makedirs(watch_path, exist_ok=True)

    event_handler = HoneyTokenEventHandler(watch_path)
    observer = Observer()
    observer.schedule(event_handler, watch_path, recursive=recursive)
    observer.start()

    ts = datetime.now().isoformat()
    with open(ALERTS_LOG, "a") as f:
        f.write(f"{ts}|WATCHDOG_STARTED|{watch_path}|Monitoring started recursively\n")

    print(f"[WATCHDOG] Monitoring: {watch_path}")
    print(f"[WATCHDOG] Logging to: {os.path.abspath(ALERTS_LOG)}")
    return observer


def stop_monitoring(observer):
    if observer and observer.is_alive():
        observer.stop()
        observer.join()
        ts = datetime.now().isoformat()
        with open(ALERTS_LOG, "a") as f:
            f.write(f"{ts}|WATCHDOG_STOPPED||Monitoring stopped\n")
        print("[WATCHDOG] Stopped.")


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "./honeytokens"
    obs = start_monitoring(target)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_monitoring(obs)
