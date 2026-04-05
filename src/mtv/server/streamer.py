"""FFmpeg stream management - direct streaming (no threading)"""

import subprocess
import logging
from typing import Optional, List

from mtv.models.movie import Movie
from mtv.utils.ffmpeg import build_stream_command

logger = logging.getLogger(__name__)


class StreamProcess:
    """Manages a single FFmpeg streaming process with direct reading"""

    def __init__(
        self,
        movie: Movie,
        seek_time: float,
        audio_stream_index: Optional[int] = None,
        subtitle_stream_indices: Optional[List[int]] = None
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
            audio_stream_index=audio_stream_index,
            subtitle_stream_indices=subtitle_stream_indices
        )
        self.command = cmd

    def start(self) -> subprocess.Popen:
        """Start FFmpeg process"""
        logger.info(
            f"Starting stream: {self.movie.filename} "
            f"at {self._format_time(self.seek_time)}"
        )

        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0  # Unbuffered
        )

        return self.process

    def read_chunk(self, size: int = 8192) -> bytes:
        """Read a chunk directly from FFmpeg stdout"""
        if not self.process:
            return b''
        
        try:
            chunk = self.process.stdout.read(size)
            if chunk:
                self.bytes_sent += len(chunk)
            return chunk
        except Exception as e:
            logger.error(f"Read error: {e}")
            return b''

    def terminate(self) -> None:
        """Stop FFmpeg and cleanup"""
        if self.process:
            self.process.terminate()
            try:
                # Wait for process to finish and capture stderr
                stderr_output = self.process.communicate(timeout=5)[1]
                if stderr_output:
                    # Log FFmpeg errors/warnings
                    stderr_str = stderr_output.decode('utf-8', errors='replace').strip()
                    if stderr_str:
                        logger.debug(f"FFmpeg output: {stderr_str[:200]}...")
            except subprocess.TimeoutExpired:
                self.process.kill()
                logger.warning("Had to kill FFmpeg process")
            self.process = None

        logger.info(
            f"Stream ended: {self.movie.filename} "
            f"(total: {self.bytes_sent / (1024*1024):.1f} MB)"
        )

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format duration as HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
