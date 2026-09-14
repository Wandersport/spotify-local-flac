"""Linux inotify directory watcher for automatic library updates on file changes."""

import os
import sys
import ctypes
import struct
import select
import threading
import time
import logging
from typing import Dict, Optional, Set
from .config import Config
from .scanner import LibraryScanner

logger = logging.getLogger(__name__)

# Linux inotify constants
IN_CLOEXEC = 0o2000000
IN_NONBLOCK = 0o0004000
IN_MODIFY = 0x00000002
IN_ATTRIB = 0x00000004
IN_CLOSE_WRITE = 0x00000008
IN_MOVED_FROM = 0x00000040
IN_MOVED_TO = 0x00000080
IN_CREATE = 0x00000100
IN_DELETE = 0x00000200
IN_DELETE_SELF = 0x00000400
IN_MOVE_SELF = 0x00000800
IN_ISDIR = 0x40000000

WATCH_MASK = IN_CLOSE_WRITE | IN_MOVED_FROM | IN_MOVED_TO | IN_CREATE | IN_DELETE | IN_DELETE_SELF | IN_MOVE_SELF


class DirectoryWatcher:
    def __init__(self, config: Config, scanner: LibraryScanner):
        self.config = config
        self.scanner = scanner
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._wd_to_path: Dict[int, str] = {}
        self._libc: Optional[ctypes.CDLL] = None
        self._inotify_fd: Optional[int] = None
        self._pipe_r: Optional[int] = None
        self._pipe_w: Optional[int] = None
        self._debounce_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    def _init_libc(self) -> bool:
        if sys.platform != "linux":
            return False
        try:
            self._libc = ctypes.CDLL("libc.so.6", use_errno=True)
            return True
        except Exception as e:
            logger.warning("Could not load libc for inotify: %s", e)
            return False

    def _add_watch_recursive(self, path: str) -> None:
        """Recursively add inotify watches for path and subdirectories."""
        if not self._libc or self._inotify_fd is None:
            return
        try:
            for root, dirs, _ in os.walk(path, followlinks=True):
                # Filter excluded dirs
                dirs[:] = [
                    d for d in dirs
                    if not any(d.startswith(".") or d.lower() in ("trash", "lost+found") for _ in [0])
                ]
                abs_root = os.path.realpath(root)
                b_path = abs_root.encode("utf-8")
                wd = self._libc.inotify_add_watch(self._inotify_fd, b_path, WATCH_MASK)
                if wd >= 0:
                    self._wd_to_path[wd] = abs_root
                else:
                    errno = ctypes.get_errno()
                    logger.debug("inotify_add_watch failed for %s: errno %d", abs_root, errno)
        except Exception as e:
            logger.warning("Error adding watches to %s: %s", path, e)

    def _trigger_debounced_scan(self) -> None:
        """Debounce rapid filesystem events before triggering scanner."""
        with self._lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(1.5, self.scanner.scan_async)
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

    def start(self) -> None:
        """Start directory watcher thread."""
        if not self.config.watch_directories:
            logger.info("Directory watching is disabled in config")
            return

        if not self._init_libc():
            logger.warning("inotify not available; directory watcher will not run")
            return

        try:
            self._inotify_fd = self._libc.inotify_init1(IN_CLOEXEC | IN_NONBLOCK)
            if self._inotify_fd < 0:
                logger.warning("inotify_init1 failed: errno %d", ctypes.get_errno())
                return

            self._pipe_r, self._pipe_w = os.pipe()
            self.running = True

            # Register configured music directories
            for d in self.config.music_directories:
                if os.path.isdir(d):
                    self._add_watch_recursive(d)

            logger.info("Directory watcher active on %d directories", len(self._wd_to_path))
            self._thread = threading.Thread(target=self._run, name="DirectoryWatcher", daemon=True)
            self._thread.start()

        except Exception as e:
            logger.error("Failed to start directory watcher: %s", e)
            self.stop()

    def _run(self) -> None:
        """Worker loop reading inotify events."""
        EVENT_FMT = "iIII"
        EVENT_SIZE = struct.calcsize(EVENT_FMT)

        while self.running and self._inotify_fd is not None and self._pipe_r is not None:
            try:
                rlist, _, _ = select.select([self._inotify_fd, self._pipe_r], [], [], 60.0)
                if self._pipe_r in rlist:
                    # Termination signaled
                    break

                if self._inotify_fd in rlist:
                    data = os.read(self._inotify_fd, 65536)
                    if not data:
                        continue

                    offset = 0
                    while offset + EVENT_SIZE <= len(data):
                        wd, mask, cookie, length = struct.unpack_from(EVENT_FMT, data, offset)
                        offset += EVENT_SIZE
                        name = ""
                        if length > 0:
                            raw_name = data[offset:offset + length]
                            name = raw_name.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
                            offset += length

                        parent_dir = self._wd_to_path.get(wd)
                        if not parent_dir:
                            continue

                        full_path = os.path.join(parent_dir, name) if name else parent_dir

                        if mask & IN_ISDIR and (mask & (IN_CREATE | IN_MOVED_TO)):
                            # New directory created: watch it
                            if os.path.isdir(full_path):
                                self._add_watch_recursive(full_path)

                        # Trigger library rescan
                        self._trigger_debounced_scan()

            except Exception as e:
                if self.running:
                    logger.debug("Exception in directory watcher loop: %s", e)
                break

    def stop(self) -> None:
        """Stop directory watcher and release resources."""
        self.running = False
        with self._lock:
            if self._debounce_timer:
                self._debounce_timer.cancel()

        if self._pipe_w is not None:
            try:
                os.write(self._pipe_w, b"\x00")
            except OSError:
                pass

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        if self._pipe_r is not None:
            try:
                os.close(self._pipe_r)
                os.close(self._pipe_w)
            except OSError:
                pass
            self._pipe_r = None
            self._pipe_w = None

        if self._inotify_fd is not None:
            try:
                os.close(self._inotify_fd)
            except OSError:
                pass
            self._inotify_fd = None

        self._wd_to_path.clear()
        logger.info("Directory watcher stopped")
