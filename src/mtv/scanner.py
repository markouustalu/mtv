"""Media folder scanner with subtitle detection"""

import logging
from pathlib import Path
from typing import List, Optional

from mtv.config import Config
from mtv.models.movie import Movie
from mtv.utils.ffprobe import get_media_info

logger = logging.getLogger(__name__)


def scan_media_folder(config: Config) -> List[Movie]:
    """
    Scan media folder for movies and their subtitles.

    Args:
        config: Application configuration

    Returns:
        List of Movie objects with metadata
    """
    media_path = Path(config.media.folder)
    movies = []

    logger.info(f"Scanning media folder: {media_path}")

    # Find all media files (exclude subtitle files and system files)
    media_files = []
    subtitle_exts = set(config.media.subtitle_extensions)
    media_exts = set(ext.lower() for ext in config.media.extensions)

    for ext in config.media.extensions:
        for file_path in media_path.glob(f'*{ext}'):
            # Only include if extension matches exactly (case-insensitive)
            if file_path.suffix.lower() in media_exts:
                media_files.append(file_path)

    logger.info(f"Found {len(media_files)} media files")

    # Process each file with progress reporting
    for idx, file_path in enumerate(media_files, start=1):
        logger.info(f"Scanning [{idx}/{len(media_files)}]: {file_path.name}")
        movie = get_media_info(str(file_path))
        if movie:
            # Look for external subtitle
            subtitle_path = find_external_subtitle(
                file_path,
                config.media.subtitle_extensions
            )
            if subtitle_path:
                movie.external_subtitle = str(subtitle_path.absolute())
                logger.debug(f"Found subtitle for {movie.filename}: {subtitle_path.name}")

            movies.append(movie)
        else:
            logger.warning(f"Failed to scan: {file_path.name}")

    logger.info(f"Successfully scanned {len(movies)} movies")
    
    return movies


def find_external_subtitle(
    movie_path: Path, 
    subtitle_extensions: List[str]
) -> Optional[Path]:
    """
    Find external subtitle file for a movie.
    
    Matching logic:
    - Same basename as movie, with subtitle extension
    - e.g., "movie.mkv" matches "movie.srt" or "movie.en.srt"
    
    Args:
        movie_path: Path to the movie file
        subtitle_extensions: List of subtitle extensions to look for
        
    Returns:
        Path to subtitle file or None
    """
    # Get movie basename without extension
    movie_stem = movie_path.stem
    
    # Try exact match first: movie.srt
    for ext in subtitle_extensions:
        subtitle_candidate = movie_path.with_name(f"{movie_stem}{ext}")
        if subtitle_candidate.exists():
            return subtitle_candidate
    
    # Try language-tagged: movie.en.srt or movie.English.srt
    # This handles cases where there might be multiple subtitle files
    parent = movie_path.parent
    for file in parent.iterdir():
        if file.is_file():
            # Check if file starts with movie name and has subtitle extension
            file_stem = file.stem
            for ext in subtitle_extensions:
                if file_stem.startswith(f"{movie_stem}.") and file.suffix.lower() in subtitle_extensions:
                    return file
    
    return None


def filter_by_language(
    movies: List[Movie], 
    prefer_english: bool = True
) -> List[Movie]:
    """
    Log warnings about movies without preferred language audio.
    
    Note: We don't filter out movies, just log warnings.
    User might want to watch non-English movies.
    
    Args:
        movies: List of movies to check
        prefer_english: Whether to prefer English audio
        
    Returns:
        Same list (no filtering, just logging)
    """
    if prefer_english:
        for movie in movies:
            if not movie.has_english_audio and movie.audio_streams:
                langs = [s.language for s in movie.audio_streams if s.language]
                logger.warning(f"{movie.filename} has no English audio (languages: {langs or 'unknown'})")
            elif not movie.audio_streams:
                logger.warning(f"{movie.filename} has no audio streams")
    
    return movies
