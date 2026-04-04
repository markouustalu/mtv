"""Main entry point for Marko TV"""

import signal
import sys
import logging
from pathlib import Path

from mtv.config import Config
from mtv.utils.logging import setup_logging
from mtv.scanner import scan_media_folder
from mtv.library import Library
from mtv.scheduler import Scheduler
from mtv.server import ThreadingHTTPServer, StreamHandler

# Setup logging first
logger = logging.getLogger('mtv')


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def main():
    """Main application entry point"""
    print("=" * 60)
    print("Marko TV (MTV) - IPTV Streaming Server")
    print("=" * 60)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Load configuration
    try:
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
        config = Config.load(str(config_path))
    except Exception as e:
        print(f"ERROR: Failed to load configuration: {e}")
        sys.exit(1)
    
    # Setup logging
    logger = setup_logging(config.logging)
    logger.info("Marko TV starting...")
    
    # Scan media folder
    logger.info("Scanning media folder...")
    movies = scan_media_folder(config)
    
    if not movies:
        logger.error("No movies found in media folder!")
        print(f"ERROR: No movies found in {config.media.folder}")
        sys.exit(1)
    
    logger.info(f"Found {len(movies)} movies")
    
    # Create library and shuffle
    library = Library()
    library.load_movies(movies)
    
    # Create scheduler
    scheduler = Scheduler(library.get_playlist(), config)
    
    # Configure handler with dependencies
    StreamHandler.library = library
    StreamHandler.scheduler = scheduler
    StreamHandler.config = config
    
    # Print startup info
    total_duration = library.get_total_duration()
    hours = int(total_duration // 3600)
    mins = int((total_duration % 3600) // 60)
    
    print("=" * 60)
    print(f"Server:    http://{config.server.host}:{config.server.port}")
    print(f"Movies:    {len(movies)}")
    print(f"Duration:  {hours}h {mins}m (total playlist)")
    print(f"M3U:       http://{config.server.host}:{config.server.port}/m3u")
    print(f"EPG:       http://{config.server.host}:{config.server.port}/epg")
    print(f"Health:    http://{config.server.host}:{config.server.port}/health")
    print("=" * 60)
    print("Press Ctrl+C to stop")
    print()
    
    # Create and start server
    server = ThreadingHTTPServer(
        (config.server.host, config.server.port),
        StreamHandler
    )
    
    logger.info(f"Server started on {config.server.host}:{config.server.port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        logger.info("Shutting down server...")
        server.shutdown()


if __name__ == "__main__":
    main()
