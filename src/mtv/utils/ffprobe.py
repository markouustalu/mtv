"""FFprobe wrapper for extracting media metadata"""

import subprocess
import json
import logging
from pathlib import Path
from typing import Optional, Tuple

from mtv.models.movie import Movie, AudioStream, SubtitleStream

logger = logging.getLogger(__name__)


def get_media_info(file_path: str) -> Optional[Movie]:
    """
    Extract metadata from a media file using ffprobe.
    
    Args:
        file_path: Path to the media file
        
    Returns:
        Movie object with metadata or None if extraction fails
    """
    path = Path(file_path)
    
    if not path.exists():
        logger.error(f"File does not exist: {file_path}")
        return None
    
    try:
        # Run ffprobe to get JSON output
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"ffprobe failed for {file_path}: {result.stderr}")
            return None
        
        data = json.loads(result.stdout)
        
        # Extract format info
        format_info = data.get('format', {})
        duration = float(format_info.get('duration', 0))
        
        # Determine container type
        filename = path.name.lower()
        if filename.endswith('.mkv'):
            container = 'mkv'
        elif filename.endswith('.mp4'):
            container = 'mp4'
        else:
            container = format_info.get('format_name', 'unknown')
        
        # Extract streams
        streams = data.get('streams', [])
        video_codec = ''
        width = 0
        height = 0
        audio_streams = []
        subtitle_streams = []
        audio_count = 0
        subtitle_count = 0

        for stream in streams:
            codec_type = stream.get('codec_type')
            codec_name = stream.get('codec_name', '')
            lang = stream.get('tags', {}).get('language')

            if codec_type == 'video':
                video_codec = codec_name
                width = stream.get('width', 0)
                height = stream.get('height', 0)

            elif codec_type == 'audio':
                channels = stream.get('channels', 2)
                sample_rate = int(stream.get('sample_rate', 48000)) if stream.get('sample_rate') else 48000
                audio_streams.append(AudioStream(
                    index=stream.get('index', 0),
                    codec=codec_name,
                    language=lang,
                    channels=channels,
                    sample_rate=sample_rate,
                    type_index=audio_count  # 0-based index within audio streams
                ))
                audio_count += 1

            elif codec_type == 'subtitle':
                subtitle_streams.append(SubtitleStream(
                    index=stream.get('index', 0),
                    codec=codec_name,
                    language=lang,
                    type_index=subtitle_count  # 0-based index within subtitle streams
                ))
                subtitle_count += 1
        
        if not duration:
            logger.warning(f"No duration found for {file_path}")
            return None
        
        return Movie(
            path=str(path.absolute()),
            filename=path.name,
            duration=duration,
            container=container,
            video_codec=video_codec,
            width=width,
            height=height,
            audio_streams=audio_streams,
            subtitle_streams=subtitle_streams
        )
        
    except subprocess.TimeoutExpired:
        logger.error(f"ffprobe timeout for {file_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse ffprobe output for {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error probing {file_path}: {e}")
        return None


def get_duration_only(file_path: str) -> Optional[float]:
    """
    Quick duration extraction without full metadata.
    Useful for initial scanning.
    
    Args:
        file_path: Path to the media file
        
    Returns:
        Duration in seconds or None if extraction fails
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return None
        
        return float(result.stdout.strip())
        
    except (subprocess.TimeoutExpired, ValueError, Exception) as e:
        logger.warning(f"Quick duration probe failed for {file_path}: {e}")
        return None
