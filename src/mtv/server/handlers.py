"""HTTP request handlers for MTV"""

import logging
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from typing import Optional
from urllib.parse import urlparse

from mtv.library import Library
from mtv.scheduler import Scheduler
from mtv.server.streamer import StreamProcess
from mtv.config import Config

logger = logging.getLogger(__name__)


class StreamHandler(BaseHTTPRequestHandler):
    """HTTP request handler for streaming"""
    
    protocol_version = 'HTTP/1.1'
    
    # These will be set by the server
    library: Optional[Library] = None
    scheduler: Optional[Scheduler] = None
    config: Optional[Config] = None
    
    def log_message(self, format, *args):
        """Suppress default HTTP logging - we do our own"""
        pass
    
    def _timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.now().strftime("%H:%M:%S")
    
    def do_HEAD(self):
        """Handle HEAD requests - reject like ErsatzTV HLS Direct"""
        logger.info(f"[{self._timestamp()}] [HEAD] Request from {self.client_address[0]}")
        
        # Reject HEAD requests (Kodi sends these for probing)
        self.send_response(405)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Allow', 'GET')
        self.end_headers()
        self.wfile.write(b'Method Not Allowed')
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        logger.info(f"[{self._timestamp()}] [GET] {path} from {self.client_address[0]}")
        
        # Route requests
        if path == '/m3u' or path == '/playlist.m3u':
            self._handle_m3u()
        elif path == '/epg' or path == '/epg.xml':
            self._handle_epg()
        elif path == '/health':
            self._handle_health()
        elif path.startswith('/stream/'):
            self._handle_stream()
        elif path in ['/', '/index.html', '/favicon.ico']:
            self._handle_root()
        else:
            self._handle_not_found()
    
    def _handle_root(self):
        """Handle root path - return forbidden"""
        logger.info("Rejecting root request")
        self.send_response(403)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Connection', 'close')
        self.send_header('Content-Length', '9')
        self.end_headers()
        self.wfile.write(b'Forbidden')
    
    def _handle_not_found(self):
        """Handle unknown paths"""
        self.send_response(404)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Connection', 'close')
        self.send_header('Content-Length', '9')
        self.end_headers()
        self.wfile.write(b'Not Found')
    
    def _handle_health(self):
        """Handle health check endpoint"""
        from datetime import timezone
        
        uptime = (datetime.now(timezone.utc).timestamp() - 
                  self.config.timetable.epoch) if self.config else 0
        
        response = {
            'status': 'ok',
            'uptime_seconds': int(uptime),
            'movies': len(self.library) if self.library else 0
        }
        
        import json
        body = json.dumps(response).encode('utf-8')
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)
    
    def _handle_m3u(self):
        """Handle M3U playlist generation"""
        from mtv.api.playlist import generate_m3u
        
        try:
            m3u_content = generate_m3u(self.library, self.config)
            body = m3u_content.encode('utf-8')
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
            logger.info("Sent M3U playlist")
        except Exception as e:
            logger.error(f"Error generating M3U: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Internal Server Error')
    
    def _handle_epg(self):
        """Handle EPG generation"""
        from mtv.api.epg import generate_epg
        
        try:
            epg_content = generate_epg(self.library, self.scheduler, self.config)
            body = epg_content.encode('utf-8')
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/xml')
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
            logger.info("Sent EPG data")
        except Exception as e:
            logger.error(f"Error generating EPG: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Internal Server Error')
    
    def _handle_stream(self):
        """Handle video stream request"""
        if not self.library or not self.scheduler:
            self.send_response(503)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Service Unavailable')
            return
        
        # Calculate current playback position
        playback = self.scheduler.get_current_playback()
        movie = playback.movie
        seek_time = playback.seek_time
        
        # Get preferred audio stream
        audio_stream_idx = movie.get_preferred_audio_stream(
            prefer_english=self.config.media.prefer_english
        ) if self.config else None
        
        logger.info(
            f"Streaming {movie.filename} at "
            f"{StreamProcess._format_time(seek_time)} "
            f"(audio stream: {audio_stream_idx})"
        )
        
        # Send response headers
        self.send_response(200)
        self.send_header('Content-Type', 'video/x-matroska')
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()
        
        # Create and start stream
        stream = StreamProcess(
            movie=movie,
            seek_time=seek_time,
            audio_stream_index=audio_stream_idx
        )
        
        try:
            stream.start()
            
            # Stream data to client
            while True:
                chunk = stream.read_chunk(self.config.streaming.buffer_size) if self.config else stream.read_chunk()
                if not chunk:
                    logger.info(f"Stream ended: {movie.filename}")
                    break
                
                self.wfile.write(chunk)
                self.wfile.flush()
                
                # Log progress every 10MB
                if stream.bytes_sent % (10 * 1024 * 1024) < len(chunk):
                    logger.debug(f"Sent {stream.bytes_sent / (1024*1024):.1f} MB")
            
        except BrokenPipeError:
            logger.info(f"Client disconnected during stream")
        except ConnectionResetError:
            logger.info(f"Connection reset by client")
        except Exception as e:
            logger.error(f"Stream error: {e}")
        finally:
            stream.terminate()
