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

    def get_preferred_audio_stream(
        self, 
        prefer_english: bool = True,
        preferred_languages: Optional[List[str]] = None
    ) -> Optional[int]:
        """
        Get 0-based index of preferred audio stream (for FFmpeg -map).

        Logic:
        - If only one stream exists (any language), use it (don't make movie mute)
        - Prefer languages from preferred_languages list (in order)
        - Fallback to first stream

        Args:
            prefer_english: Legacy parameter, kept for compatibility
            preferred_languages: List of language codes in priority order

        Returns:
            type_index of preferred audio stream
        """
        # If only one stream, use it regardless of language
        if len(self.audio_streams) == 1:
            return 0

        # Determine which languages to prefer
        if preferred_languages is None:
            # Default to English if not specified
            preferred_languages = ['en', 'eng']

        # Try to find a stream with preferred language
        for stream in self.audio_streams:
            if stream.language in preferred_languages:
                return stream.type_index

        # Fallback to first stream
        return 0 if self.audio_streams else None

    def get_preferred_subtitle_streams(
        self, 
        has_external_subtitle: bool = False,
        preferred_languages: Optional[List[str]] = None
    ) -> List[int]:
        """
        Get type indices of preferred subtitle streams (for FFmpeg -map).

        Logic:
        - If external subtitle present: return empty list (external will be handled separately)
        - Prefer languages from preferred_languages list (in order)
        - If normal and SDH both present for same language, prefer normal first
        - If no preferred language found, include Unknown language streams
        - Exclude other known languages

        Args:
            has_external_subtitle: Whether external subtitle file exists
            preferred_languages: List of language codes in priority order

        Returns:
            List of subtitle type indices in priority order
        """
        # If external subtitle is present, don't include any internal streams
        if has_external_subtitle:
            return []

        if not self.subtitle_streams:
            return []

        # Determine which languages to prefer
        if preferred_languages is None:
            # Default to English if not specified
            preferred_languages = ['en', 'eng']

        # Separate streams by language and type
        preferred_streams = []
        unknown_streams = []

        for stream in self.subtitle_streams:
            lang = stream.language
            codec = stream.codec.lower()

            # Check if language is in preferred list
            if lang in preferred_languages:
                # Separate normal vs SDH
                is_sdh = 'sdh' in codec or 'hearing' in codec
                preferred_streams.append((stream.type_index, is_sdh, lang))
            elif lang is None or lang == 'und':
                # Unknown language
                unknown_streams.append(stream.type_index)

        # Sort preferred streams: by language priority, then normal before SDH
        lang_priority = {lang: idx for idx, lang in enumerate(preferred_languages)}
        preferred_streams.sort(key=lambda x: (lang_priority.get(x[2], 999), x[1]))

        # Return preferred streams first, then unknown if no preferred found
        if preferred_streams:
            return [idx for idx, _, _ in preferred_streams]
        elif unknown_streams:
            return unknown_streams
        else:
            # No suitable streams found
            return []
