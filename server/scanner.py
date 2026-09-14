"""Library scanner for recursively finding and indexing audio files."""

import os
import fnmatch
import logging
import threading
import time
from typing import List, Dict, Any, Optional, Set
from .config import Config
from .db import Database
from .metadata import extract_metadata

logger = logging.getLogger(__name__)


class LibraryScanner:
    def __init__(self, config: Config, db: Database):
        self.config = config
        self.db = db
        self._lock = threading.Lock()
        self.is_scanning = False
        self.last_scan_time: Optional[float] = None
        self.current_file: Optional[str] = None
        self.tracks_found: int = 0
        self.tracks_indexed: int = 0
        self.tracks_updated: int = 0
        self.tracks_removed: int = 0
        self.errors: int = 0

    def _should_exclude(self, path: str, name: str, is_dir: bool = False) -> bool:
        """Check if filename or directory path matches exclusion criteria.

        Semantics:
        - Hidden directories (e.g. .git, .cache, hidden metadata dirs) are skipped.
        - Directory/path patterns like *recycle*, *trash*, *lost+found* are skipped.
        - Known junk files (e.g. .DS_Store, .directory, thumbs.db, AppleDouble ._*) are skipped.
        - Supported audio files (.flac, .mp3, .m4a, .mp4, .wav, etc.) are NOT excluded
          merely because their basename begins with '.' (e.g. '.223 song.mp3', '.hidden.flac').
        """
        # 1. Directory exclusion
        if is_dir:
            if name.startswith("."):
                return True
            for pat in self.config.exclude_patterns:
                if fnmatch.fnmatch(name.lower(), pat.lower()) or fnmatch.fnmatch(path.lower(), pat.lower()):
                    return True
            return False

        # 2. File exclusion
        # Skip AppleDouble resource fork files (._*)
        if name.startswith("._"):
            return True

        # Skip known OS junk/metadata files
        if name.lower() in (".ds_store", ".directory", ".localized", "thumbs.db", "desktop.ini"):
            return True

        ext = os.path.splitext(name)[1].lower()
        is_supported_audio = ext in self.config.supported_extensions

        # Evaluate exclusion patterns
        for pat in self.config.exclude_patterns:
            pat_lower = pat.lower()
            # If pattern is '.*', do NOT exclude supported audio files that happen to start with '.'
            if pat_lower == ".*" and is_supported_audio:
                continue

            if fnmatch.fnmatch(name.lower(), pat_lower) or fnmatch.fnmatch(path.lower(), pat_lower):
                return True

        return False

    def scan_sync(self) -> Dict[str, Any]:
        """Synchronously scan all configured music directories."""
        with self._lock:
            self.is_scanning = True
            self.tracks_found = 0
            self.tracks_indexed = 0
            self.tracks_updated = 0
            self.tracks_removed = 0
            self.errors = 0
            start_time = time.time()

            try:
                extensions = set(self.config.supported_extensions)
                seen_paths: Set[str] = set()

                for root_dir in self.config.music_directories:
                    if not os.path.isdir(root_dir):
                        logger.warning("Music directory does not exist: %s", root_dir)
                        continue

                    logger.info("Scanning music directory: %s", root_dir)
                    for dirpath, dirnames, filenames in os.walk(root_dir, followlinks=True):
                        # Filter directories in place to avoid descending into excluded dirs
                        dirnames[:] = [
                            d for d in dirnames
                            if not self._should_exclude(os.path.join(dirpath, d), d, is_dir=True)
                        ]

                        for fname in filenames:
                            if self._should_exclude(os.path.join(dirpath, fname), fname, is_dir=False):
                                continue

                            ext = os.path.splitext(fname)[1].lower()
                            if ext in extensions:
                                full_path = os.path.realpath(os.path.join(dirpath, fname))
                                seen_paths.add(full_path)
                                self.tracks_found += 1
                                self.current_file = full_path

                                try:
                                    stat = os.stat(full_path)
                                    mtime = stat.st_mtime
                                    size = stat.st_size

                                    # Fast incremental check: if unchanged, skip metadata parse
                                    cached_info = self.db.get_track_mtime(full_path)
                                    if cached_info is not None:
                                        c_mtime, c_size = cached_info
                                        if abs(c_mtime - mtime) < 0.001 and c_size == size:
                                            continue

                                    # Extract metadata
                                    meta = extract_metadata(full_path)
                                    if meta:
                                        self.db.upsert_track(meta)
                                        if cached_info is None:
                                            self.tracks_indexed += 1
                                        else:
                                            self.tracks_updated += 1
                                    else:
                                        self.errors += 1
                                except Exception as e:
                                    logger.warning("Error processing %s: %s", full_path, e)
                                    self.errors += 1

                # Clean up tracks that were deleted or moved
                all_db_paths = self.db.get_all_paths()
                missing = [p for p in all_db_paths if p not in seen_paths]
                # Double check that missing files truly don't exist on disk before deleting
                truly_missing = [p for p in missing if not os.path.exists(p)]
                if truly_missing:
                    self.tracks_removed = self.db.delete_tracks_by_paths(truly_missing)
                    logger.info("Removed %d missing tracks from library database", self.tracks_removed)

                self.last_scan_time = time.time()
                elapsed = self.last_scan_time - start_time
                logger.info(
                    "Library scan completed in %.2fs: %d found, %d indexed, %d updated, %d removed, %d errors",
                    elapsed, self.tracks_found, self.tracks_indexed, self.tracks_updated, self.tracks_removed, self.errors
                )

                return {
                    "success": True,
                    "elapsed_seconds": round(elapsed, 2),
                    "tracks_found": self.tracks_found,
                    "tracks_indexed": self.tracks_indexed,
                    "tracks_updated": self.tracks_updated,
                    "tracks_removed": self.tracks_removed,
                    "errors": self.errors
                }

            finally:
                self.is_scanning = False
                self.current_file = None

    def scan_async(self) -> None:
        """Trigger library scan in background thread if not already scanning."""
        if self.is_scanning:
            return
        thread = threading.Thread(target=self.scan_sync, name="LibraryScanner", daemon=True)
        thread.start()

    def get_status(self) -> Dict[str, Any]:
        """Current scanner status."""
        return {
            "is_scanning": self.is_scanning,
            "last_scan_time": self.last_scan_time,
            "current_file": self.current_file,
            "tracks_found": self.tracks_found,
            "tracks_indexed": self.tracks_indexed,
            "tracks_updated": self.tracks_updated,
            "tracks_removed": self.tracks_removed,
            "errors": self.errors
        }
