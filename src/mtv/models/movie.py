"""Models for MTV"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class AudioStream:
    """Represents an audio stream in a media file"""
    index: int
    codec: str
    language: Optional[str]
    channels: int
    sample_rate: int


@dataclass
class SubtitleStream:
    """Represents a subtitle stream in a media file"""
    index: int
    codec: str
    language: Optional[str]


@dataclass
class Movie:
    """Represents a movie file with metadata"""
    path: str
    filename: str
    duration: float  # in seconds
    container: str  # 'mkv' or 'mp4'
    video_codec: str
    width: int
    height: int
    audio_streams: List[AudioStream]
    subtitle_streams: List[SubtitleStream]
    external_subtitle: Optional[str] = None  # Path to external subtitle file
    
    @property
    def title(self) -> str:
        """Extract title from filename"""
        # Simple extraction: remove extension and clean up
        title = self.filename.rsplit('.', 1)[0]
        # Remove common patterns like year, resolution
        import re
        title = re.sub(r'\s*\d{4}\s*', ' ', title)
        title = re.sub(r'\s*(1080p|720p|4k|2160p|blu-ray|bluray|web-dl)\s*', ' ', title, flags=re.IGNORECASE)
        return title.strip()
    
    @property
    def has_english_audio(self) -> bool:
        """Check if movie has English audio stream"""
        return any(stream.language == 'en' for stream in self.audio_streams)
    
    def get_preferred_audio_stream(self, prefer_english: bool = True) -> Optional[int]:
        """Get index of preferred audio stream"""
        if prefer_english:
            for stream in self.audio_streams:
                if stream.language == 'en':
                    return stream.index
        # Fallback to first stream
        return self.audio_streams[0].index if self.audio_streams else None
