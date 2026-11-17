import asyncio
import inspect
import logging
import time
from typing import Callable, Optional
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os

logger = logging.getLogger("aurora.watcher")


class VaultEvent:
    def __init__(self, event_type: str, path: str, timestamp: datetime):
        self.event_type = event_type
        self.path = path
        self.timestamp = timestamp


class VaultChangeHandler(FileSystemEventHandler):
    """Receives watchdog events (on a background thread) and dispatches them.

    Watchdog calls these handlers from its own observer thread. If the callback
    is a coroutine function, it must be scheduled on the main asyncio loop with
    run_coroutine_threadsafe — calling it directly would only create a coroutine
    object that is never awaited (and the re-index would silently never happen).
    """

    def __init__(self, callback: Callable, debounce_seconds: float = 1.0,
                 loop: Optional[asyncio.AbstractEventLoop] = None):
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.loop = loop
        self._is_async = inspect.iscoroutinefunction(callback)
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

    def _dispatch(self, event_type: str, path: str) -> None:
        vault_event = VaultEvent(event_type, path, datetime.utcnow())
        try:
            if self._is_async:
                if self.loop is None or self.loop.is_closed():
                    logger.warning("No running event loop for async watcher callback; dropping event")
                    return
                asyncio.run_coroutine_threadsafe(self.callback(vault_event), self.loop)
            else:
                self.callback(vault_event)
        except Exception as e:
            logger.error(f"Watcher callback failed for {path}: {e}")

    def on_created(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            self._dispatch('created', event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            self._dispatch('modified', event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            self._dispatch('deleted', event.src_path)

    def on_moved(self, event):
        # Renames in Obsidian arrive as moves: treat as delete old + create new
        if event.is_directory:
            return
        if event.src_path.endswith('.md'):
            self._dispatch('deleted', event.src_path)
        dest = getattr(event, 'dest_path', None)
        if dest and self._should_process(dest):
            self._dispatch('created', dest)


class VaultWatcher:
    def __init__(self, vault_path: str, callback: Callable, debounce_seconds: float = 1.0):
        self.vault_path = vault_path
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.observer = Observer()
        self.handler: Optional[VaultChangeHandler] = None

    def start(self):
        # Capture the running loop (start() is called from the FastAPI lifespan,
        # i.e. inside the main event loop) so async callbacks can be scheduled on it.
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        self.handler = VaultChangeHandler(self.callback, self.debounce_seconds, loop)
        self.observer.schedule(self.handler, self.vault_path, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
