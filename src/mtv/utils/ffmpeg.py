"""FFmpeg command builder for streaming"""

import logging
from typing import List, Optional

from mtv.models.movie import Movie

logger = logging.getLogger(__name__)


def build_stream_command(
    movie: Movie,
    seek_time: float,
    subtitle_path: Optional[str] = None,
    audio_stream_index: Optional[int] = None,
    subtitle_stream_indices: Optional[List[int]] = None
) -> List[str]:
    """
    Build FFmpeg command for streaming a movie.

    Strategy:
    - Always output as MKV container (handles subtitles better)
    - Use -c copy for true copy-mode (no transcoding)
    - Double seek (input + output) for accuracy
    - Select specific audio stream if requested
    - Embed external subtitle if provided (takes priority over internal)
    - Include multiple subtitle streams if needed
    - Set first subtitle stream as default

    Args:
        movie: Movie to stream
        seek_time: Position to start streaming (seconds)
        subtitle_path: Optional external subtitle file
        audio_stream_index: Optional specific audio stream index to include
        subtitle_stream_indices: List of internal subtitle stream indices to include

    Returns:
        List of command line arguments for FFmpeg
    """
    cmd = [
        'ffmpeg',
        '-hide_banner',
        '-ss', f'{seek_time:.2f}',      # Input seek (fast)
        '-i', movie.path,               # Input file
    ]

    # Track if we have external subtitle
    has_external_subtitle = subtitle_path is not None

    # Add external subtitle input if provided
    if has_external_subtitle:
        cmd.extend([
            '-ss', f'{seek_time:.2f}',  # Input seek for subtitle file
            '-i', subtitle_path,        # Subtitle input
        ])

    # Select specific audio stream if requested (use type_index, not overall index)
    if audio_stream_index is not None:
        # Map video and selected audio (audio_stream_index is already 0-based type index)
        cmd.extend([
            '-map', '0:v:0',                    # First video stream
            '-map', f'0:a:{audio_stream_index}',  # Selected audio stream (by type index)
        ])
    else:
        # Map all video and audio
        cmd.extend([
            '-map', '0:v:0',            # First video stream
            '-map', '0:a?',             # All audio streams (if any)
        ])

    # Exclude chapters
    cmd.extend([
        '-map_chapters', '-1',          # Don't copy chapters
    ])

    # Handle subtitle mapping
    subtitle_disposition_index = 0  # Track which subtitle to set as default

    if has_external_subtitle:
        # External subtitle only - no internal streams
        cmd.extend([
            '-map', '1:s:0',            # External subtitle stream
        ])
        subtitle_disposition_index = 0  # External subtitle will be first in output
    elif subtitle_stream_indices:
        # Map selected internal subtitle streams
        for idx in subtitle_stream_indices:
            cmd.extend([
                '-map', f'0:s:{idx}',   # Selected subtitle stream
            ])
        if subtitle_stream_indices:
            subtitle_disposition_index = 0  # First mapped subtitle
    # else: no subtitles to map

    # Output options
    cmd.extend([
        '-c', 'copy',                   # Copy all streams (no transcoding)
        '-f', 'matroska',               # Always output as MKV
    ])

    # Set default subtitle disposition if we have subtitles
    if has_external_subtitle or subtitle_stream_indices:
        # Use -disposition to mark first subtitle as default
        # Syntax: -disposition:s:<index> default
        cmd.extend([
            '-disposition:s:0', 'default'
        ])

    cmd.extend([
        'pipe:1'                        # Output to stdout
    ])

    logger.info(f"FFmpeg command: {' '.join(cmd)}")
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
