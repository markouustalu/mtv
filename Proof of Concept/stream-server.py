#!/usr/bin/env python3
"""
Simple MKV streaming server for live TV testing.
Handles HEAD requests properly (Kodi sends HEAD before GET).
Streams from a fixed seek position for each client connection.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import subprocess
import sys
import threading
from datetime import datetime

def timestamp():
    """Return current timestamp string"""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

# Configuration
MOVIE_PATH = "/home/marko/movie.mkv"
SUBTITLE_PATH = "/home/marko/movie.srt"  # Not used in this example, but can be added to ffmpeg command
SEEK_TIME = "00:30:00"  # Change this to test different start times
PORT = 8555

class StreamHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_HEAD(self):
        """Handle HEAD request - reject like ErsatzTV HLS Direct mode"""
        print(f"[{timestamp()}] [HEAD] Request from {self.client_address[0]} - Rejecting (like ErsatzTV HLS Direct)")
        
        # ErsatzTV HLS Direct mode doesn't support HEAD - return 405
        self.send_response(405)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Allow', 'GET')
        self.end_headers()
        self.wfile.write(b'Method Not Allowed')
        print(f"[{timestamp()}] [HEAD] Sent 405 Method Not Allowed")

    def do_GET(self):
        """Handle GET request - stream the video"""
        print(f"[{timestamp()}] [GET] Request from {self.client_address[0]}")
        print(f"[{timestamp()}] [GET] Path: {self.path}")
        print(f"[{timestamp()}] [GET] Headers: {dict(self.headers)}")

        # Reject requests to root or unknown paths
        if self.path in ['/', '/index.html', '/favicon.ico']:
            print(f"[{timestamp()}] [GET] Rejecting root/favicon request")
            self.send_response(403)  # Forbidden instead of Not Found
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Connection', 'close')
            self.send_header('Content-Length', '9')
            self.end_headers()
            self.wfile.write(b'Forbidden')
            self.wfile.flush()
            self.close_connection = True  # Force connection close
            print(f"[{timestamp()}] [GET] Rejected with 403, connection closed")
            return

        # Check for Range header (Kodi might use it)
        range_header = self.headers.get('Range')
        if range_header:
            print(f"[{timestamp()}] [GET] Range header: {range_header}")
            
            # Kodi sends Range: bytes=0-1 to probe the file
            # For live streaming, we ignore range and stream from seek time
            # But we need to detect probe requests vs actual playback
            if range_header == 'bytes=0-1':
                print(f"[{timestamp()}] [GET] Probe request - sending 2 bytes then closing")
                # Send minimal MKV header to satisfy the probe
                self.send_response(206)  # Partial Content
                self.send_header('Content-Type', 'video/x-matroska')
                self.send_header('Content-Range', 'bytes 0-1/*')
                self.send_header('Connection', 'close')
                self.end_headers()
                # Send 2 bytes of MKV header (EBML header start)
                self.wfile.write(b'\x1a\x45')  # EBML signature
                self.wfile.flush()
                print(f"[{timestamp()}] [GET] Probe complete")
                return
        
        print(f"[{timestamp()}] [GET] Starting stream from {SEEK_TIME}")
        
        self.send_response(200)
        self.send_header('Content-Type', 'video/x-matroska')
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()
        print(f"[{timestamp()}] [GET] Response headers sent")

        cmd = [
            'ffmpeg',
            '-re',                    # Read input at native frame rate
            '-ss', SEEK_TIME,         # Seek to start time
            '-i', MOVIE_PATH,         # Input file
            '-ss', SEEK_TIME,         # Seek to start time
            '-i', SUBTITLE_PATH,      # Subtitle file (optional)
            '-c', 'copy',             # Copy streams (no transcoding)
            '-f', 'matroska',         # Output format
            'pipe:1'                  # Output to stdout
        ]

        print(f"[{timestamp()}] [FFMPEG] {' '.join(cmd)}")
        
        # Capture both stdout and stderr
        proc = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            bufsize=8192
        )

        bytes_sent = 0
        try:
            while True:
                chunk = proc.stdout.read(8192)
                if not chunk:
                    print(f"[{timestamp()}] [STREAM] End of stream (total: {bytes_sent / (1024*1024):.1f} MB)")
                    break
                self.wfile.write(chunk)
                self.wfile.flush()  # Critical for real-time streaming
                bytes_sent += len(chunk)
                
                # Log progress every 10MB
                if bytes_sent % (10 * 1024 * 1024) < len(chunk):
                    print(f"[{timestamp()}] [STREAM] Sent {bytes_sent / (1024*1024):.1f} MB")
        
        except BrokenPipeError:
            print(f"[{timestamp()}] [STREAM] Client disconnected (total: {bytes_sent / (1024*1024):.1f} MB)")
        except ConnectionResetError:
            print(f"[{timestamp()}] [STREAM] Connection reset by client (total: {bytes_sent / (1024*1024):.1f} MB)")
        finally:
            proc.terminate()
            try:
                stderr_output = proc.communicate(timeout=5)[1]
                if stderr_output:
                    print(f"[{timestamp()}] [FFMPEG STDERR] {stderr_output.decode('utf-8', errors='replace')}")
            except subprocess.TimeoutExpired:
                proc.kill()
                print(f"[{timestamp()}] [FFMPEG] Had to kill process")
            print(f"[{timestamp()}] [FFMPEG] Process stopped")

    def log_message(self, format, *args):
        """Suppress default HTTP logging"""
        pass

def main():
    if not MOVIE_PATH or not MOVIE_PATH.startswith("/"):
        print("ERROR: Please set MOVIE_PATH to an absolute path in the script")
        sys.exit(1)

    print("=" * 60)
    print("MKV Live Streaming Server")
    print("=" * 60)
    print(f"Movie: {MOVIE_PATH}")
    print(f"Seek:  {SEEK_TIME}")
    print(f"Port:  {PORT}")
    print(f"URL:   http://0.0.0.0:{PORT}/")
    print("=" * 60)
    print("Press Ctrl+C to stop")
    print()

    # Use ThreadingHTTPServer to handle multiple connections simultaneously
    class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True  # Threads die when main server stops
    
    server = ThreadingHTTPServer(('0.0.0.0', PORT), StreamHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
        server.shutdown()

if __name__ == '__main__':
    main()
