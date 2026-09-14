"""Main entry point for Spotify Local FLAC companion daemon."""

import os
import sys
import signal
import logging
import argparse
import threading
if __package__ is None or __package__ == "":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from server.config import Config
    from server.db import Database
    from server.scanner import LibraryScanner
    from server.watcher import DirectoryWatcher
    from server.app import ThreadedHTTPServer, APIHandler
else:
    from .config import Config
    from .db import Database
    from .scanner import LibraryScanner
    from .watcher import DirectoryWatcher
    from .app import ThreadedHTTPServer, APIHandler

logger = logging.getLogger("spotify_local_flac")


def setup_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] (%(threadName)s) %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def run_server(config_path: str = None, host: str = None, port: int = None, scan_now: bool = False) -> None:
    config = Config(config_path)
    if host:
        config.data["host"] = host
    if port:
        config.data["port"] = port

    setup_logging(config.log_level)
    logger.info("Starting Spotify Local FLAC companion service v1.0.0")
    logger.info("Host: %s, Port: %d", config.host, config.port)
    logger.info("Music directories: %s", config.music_directories)
    logger.info("Database: %s", config.database_path)

    db = Database(config.database_path)
    scanner = LibraryScanner(config, db)
    watcher = DirectoryWatcher(config, scanner)

    # Attach shared singletons to APIHandler
    APIHandler.config = config
    APIHandler.db = db
    APIHandler.scanner = scanner
    APIHandler.watcher = watcher

    server = ThreadedHTTPServer((config.host, config.port), APIHandler)

    shutdown_event = threading.Event()

    def handle_signal(sig, frame):
        logger.info("Signal %d received, shutting down gracefully...", sig)
        shutdown_event.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Initial scan: sync if requested, otherwise async
    if scan_now:
        logger.info("Performing synchronous initial scan...")
        scanner.scan_sync()
    else:
        logger.info("Starting asynchronous initial scan...")
        scanner.scan_async()

    # Start directory watcher
    watcher.start()

    logger.info("Server listening at http://%s:%d", config.host, config.port)
    try:
        server.serve_forever()
    finally:
        logger.info("Stopping directory watcher...")
        watcher.stop()
        server.server_close()
        logger.info("Service shut down cleanly.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Spotify Local FLAC Companion Service")
    parser.add_argument("--config", "-c", help="Path to config.json")
    parser.add_argument("--host", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, help="Bind port (default: 18492)")
    parser.add_argument("--scan-now", action="store_true", help="Perform synchronous library scan on startup")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()
    if args.debug:
        os.environ["LOG_LEVEL"] = "DEBUG"

    run_server(
        config_path=args.config,
        host=args.host,
        port=args.port,
        scan_now=args.scan_now
    )


if __name__ == "__main__":
    main()
