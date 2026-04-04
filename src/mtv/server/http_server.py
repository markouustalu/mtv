"""HTTP server wrapper"""

from http.server import HTTPServer
from socketserver import ThreadingMixIn
import logging

logger = logging.getLogger(__name__)


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Threaded HTTP server that handles each request in a new thread"""
    daemon_threads = True  # Threads die when main server stops
    allow_reuse_address = True  # Allow quick restart


def create_server(host: str, port: int, handler) -> ThreadingHTTPServer:
    """
    Create and configure HTTP server.
    
    Args:
        host: Bind address
        port: Bind port
        handler: Request handler class
        
    Returns:
        Configured HTTP server instance
    """
    server = ThreadingHTTPServer((host, port), handler)
    logger.info(f"HTTP server created on {host}:{port}")
    return server
