"""Models for MTV"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class AudioStream:
    """Represents an audio stream in a media file"""
    index: int  # Overall stream index from ffprobe
    codec: str
    language: Optional[str]
    channels: int
    sample_rate: int
    type_index: int = -1  # Index within audio streams (0 = first audio, etc.)


@dataclass
class SubtitleStream:
    """Represents a subtitle stream in a media file"""
    index: int  # Overall stream index from ffprobe
    codec: str
    language: Optional[str]
    type_index: int = -1  # Index within subtitle streams (0 = first subtitle, etc.)


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
        """Extract title from filename - just remove extension"""
        return self.filename.rsplit('.', 1)[0]
    
    @property
    def has_english_audio(self) -> bool:
        """Check if movie has English audio stream"""
        return any(stream.language == 'en' for stream in self.audio_streams)

    def get_preferred_audio_stream(self, prefer_english: bool = True) -> Optional[int]:
        """
        Get 0-based index of preferred audio stream (for FFmpeg -map).

        Logic:
        - Prefer English audio (en or eng)
        - If only one stream exists (any language), use it (don't make movie mute)
        - Fallback to first stream
        """
        # If only one stream, use it regardless of language
        if len(self.audio_streams) == 1:
            return 0

        if prefer_english:
            for stream in self.audio_streams:
                # Check for English (both 'en' and 'eng' tags)
                if stream.language in ('en', 'eng'):
                    return stream.type_index

        # Fallback to first stream
        return 0 if self.audio_streams else None

    def get_preferred_subtitle_streams(self, has_external_subtitle: bool = False) -> List[int]:
        """
        Get type indices of preferred subtitle streams (for FFmpeg -map).

        Logic:
        - If external subtitle present: return empty list (external will be handled separately)
        - Prefer English subtitles (en or eng)
        - If normal and SDH both present, prefer normal first
        - If no English, include Unknown language streams
        - Exclude other known languages

        Returns:
            List of subtitle type indices (0 = first subtitle, 1 = second, etc.) in priority order
        """
        # If external subtitle is present, don't include any internal streams
        if has_external_subtitle:
            return []

        if not self.subtitle_streams:
            return []

        # Separate streams by language and type
        english_streams = []
        unknown_streams = []

        for stream in self.subtitle_streams:
            lang = stream.language
            codec = stream.codec.lower()

            # Check if English
            if lang in ('en', 'eng'):
                # Separate normal vs SDH
                is_sdh = 'sdh' in codec or 'hearing' in codec
                english_streams.append((stream.type_index, is_sdh))
            elif lang is None or lang == 'und':
                # Unknown language
                unknown_streams.append(stream.type_index)

        # Sort English streams: normal first, then SDH
        english_streams.sort(key=lambda x: x[1])  # False (normal) before True (SDH)

        # Return English streams first, then unknown if no English
        if english_streams:
            return [idx for idx, _ in english_streams]
        elif unknown_streams:
            return unknown_streams
        else:
            # No suitable streams found
            return []
