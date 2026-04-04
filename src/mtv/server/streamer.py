"""FFmpeg stream management"""

import subprocess
import logging
from typing import Optional

from mtv.models.movie import Movie
from mtv.utils.ffmpeg import build_stream_command

logger = logging.getLogger(__name__)


class StreamProcess:
    """Manages a single FFmpeg streaming process"""
    
    def __init__(
        self,
        movie: Movie,
        seek_time: float,
        audio_stream_index: Optional[int] = None
    ):
        self.movie = movie
        self.seek_time = seek_time
        self.process: Optional[subprocess.Popen] = None
        self.bytes_sent = 0
        
        # Build command
        cmd = build_stream_command(
            movie=movie,
            seek_time=seek_time,
            subtitle_path=movie.external_subtitle,
            audio_stream_index=audio_stream_index
        )
        self.command = cmd
    
    def start(self) -> subprocess.Popen:
        """
        Start the FFmpeg process.
        
        Returns:
            Subprocess instance
        """
        logger.info(
            f"Starting stream: {self.movie.filename} "
            f"at {self._format_time(self.seek_time)}"
        )
        
        try:
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=8192,
                creationflags=subprocess.CREATE_NO_WINDOW  # Windows: don't show console
            )
            return self.process
        except Exception as e:
            logger.error(f"Failed to start FFmpeg: {e}")
            raise
    
    def read_chunk(self, size: int = 8192) -> bytes:
        """
        Read a chunk of data from FFmpeg output.
        
        Args:
            size: Number of bytes to read
            
        Returns:
            Bytes read (may be empty if EOF)
        """
        if not self.process:
            return b''
        
        try:
            chunk = self.process.stdout.read(size) if self.process.stdout else b''
            if chunk:
                self.bytes_sent += len(chunk)
            return chunk
        except Exception as e:
            logger.error(f"Error reading from FFmpeg: {e}")
            return b''
    
    def terminate(self) -> None:
        """Terminate the FFmpeg process"""
        if self.process:
            try:
                self.process.terminate()
                try:
                    stderr = self.process.communicate(timeout=5)[1]
                    if stderr:
                        stderr_str = stderr.decode('utf-8', errors='replace').strip()
                        # Log last few lines of stderr
                        if stderr_str:
                            lines = stderr_str.split('\n')[-5:]
                            logger.debug(f"FFmpeg output: {' '.join(lines)}")
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    logger.warning("Had to kill FFmpeg process")
                
                logger.info(
                    f"Stream ended: {self.movie.filename} "
                    f"(total: {self.bytes_sent / (1024*1024):.1f} MB)"
                )
            except Exception as e:
                logger.error(f"Error terminating FFmpeg: {e}")
            finally:
                self.process = None
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format time as HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
