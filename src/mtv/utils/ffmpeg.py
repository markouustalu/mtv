"""FFmpeg command builder for streaming"""

import logging
from typing import List, Optional

from mtv.models.movie import Movie

logger = logging.getLogger(__name__)


def build_stream_command(
    movie: Movie,
    seek_time: float,
    subtitle_path: Optional[str] = None,
    audio_stream_index: Optional[int] = None
) -> List[str]:
    """
    Build FFmpeg command for streaming a movie.
    
    Strategy:
    - Always output as MKV container (handles subtitles better)
    - Use -c copy for true copy-mode (no transcoding)
    - Double seek (input + output) for accuracy
    - Select specific audio stream if requested
    - Embed external subtitle if provided
    
    Args:
        movie: Movie to stream
        seek_time: Position to start streaming (seconds)
        subtitle_path: Optional external subtitle file
        audio_stream_index: Optional specific audio stream index to include
        
    Returns:
        List of command line arguments for FFmpeg
    """
    cmd = [
        'ffmpeg',
        '-re',                          # Read input at native frame rate
        '-ss', f'{seek_time:.2f}',      # Input seek (fast)
        '-i', movie.path,               # Input file
    ]
    
    # Select specific audio stream if requested
    if audio_stream_index is not None:
        # Map video and selected audio
        cmd.extend([
            '-map', '0:v:0',            # First video stream
            '-map', f'0:a:{audio_stream_index}',  # Selected audio stream
        ])
    else:
        # Map all video and audio
        cmd.extend([
            '-map', '0:v:0',            # First video stream
            '-map', '0:a?',             # All audio streams (if any)
        ])
    
    # Add external subtitle if provided
    if subtitle_path:
        cmd.extend([
            '-ss', f'{seek_time:.2f}',  # Seek subtitle file too
            '-i', subtitle_path,        # Subtitle input
        ])
        # Map subtitle with format suitable for MKV
        cmd.extend([
            '-map', '1:s:0',            # Subtitle stream
        ])
    
    # Output options
    cmd.extend([
        '-ss', f'{seek_time:.2f}',      # Output seek (precise)
        '-c', 'copy',                   # Copy all streams (no transcoding)
        '-f', 'matroska',               # Always output as MKV
        '-avoid_negative_ts', 'make_zero',  # Avoid negative timestamps
        'pipe:1'                        # Output to stdout
    ])
    
    logger.debug(f"FFmpeg command: {' '.join(cmd)}")
    return cmd


def build_ffprobe_duration_command(file_path: str) -> List[str]:
    """
    Build FFprobe command for quick duration extraction.
    
    Args:
        file_path: Path to media file
        
    Returns:
        List of command line arguments for FFprobe
    """
    return [
        'ffprobe',
        '-v', 'quiet',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        file_path
    ]
