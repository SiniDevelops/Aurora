import time
from typing import Callable
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os

class VaultEvent:
    def __init__(self, event_type: str, path: str, timestamp: datetime):
        self.event_type = event_type
        self.path = path
        self.timestamp = timestamp

class VaultChangeHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable, debounce_seconds: float = 1.0):
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._last_event_time = {}

    def _should_process(self, path: str) -> bool:
        if not path.endswith('.md'):
            return False
            
        excludes = ['.obsidian', '.trash', '.git']
        for ex in excludes:
            if f"{os.sep}{ex}{os.sep}" in path or path.endswith(ex):
                return False
                
        now = time.time()
        if path in self._last_event_time:
            if now - self._last_event_time[path] < self.debounce_seconds:
                return False
        self._last_event_time[path] = now
        return True

    def on_created(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            self.callback(VaultEvent('created', event.src_path, datetime.utcnow()))

    def on_modified(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            self.callback(VaultEvent('modified', event.src_path, datetime.utcnow()))

    def on_deleted(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            self.callback(VaultEvent('deleted', event.src_path, datetime.utcnow()))

class VaultWatcher:
    def __init__(self, vault_path: str, callback: Callable, debounce_seconds: float = 1.0):
        self.vault_path = vault_path
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.observer = Observer()
        self.handler = VaultChangeHandler(self.callback, self.debounce_seconds)

    def start(self):
        self.observer.schedule(self.handler, self.vault_path, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
