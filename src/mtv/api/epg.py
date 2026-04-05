"""XMLTV EPG generation"""

from datetime import datetime, timezone, timedelta
from typing import List

from mtv.library import Library
from mtv.scheduler import Scheduler
from mtv.config import Config


def generate_epg(library: Library, scheduler: Scheduler, config: Config) -> str:
    """
    Generate XMLTV EPG data using fixed epoch timetable.

    Starts from currently playing movie and includes:
    - If playlist duration >= 24 hours: All movies in the playlist
    - If playlist duration < 24 hours: Enough cycles to reach at least 24 hours

    Uses fixed epoch for deterministic timestamps (like ErsatzTV).

    Args:
        library: Movie library
        scheduler: Scheduler with timetable
        config: Application configuration

    Returns:
        XMLTV XML content as string
    """
    lines = []

    # XML declaration
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<tv>')

    # Channel definition (must match tvg-id in M3U)
    lines.append('  <channel id="mtv">')
    lines.append('    <display-name>MTV</display-name>')
    lines.append('  </channel>')

    # Get current playback info to find starting movie
    now = datetime.now(timezone.utc)
    current = scheduler.get_current_playback(now)

    # Determine which movies to include
    min_duration_hours = 24
    min_duration_seconds = min_duration_hours * 3600

    if scheduler.total_duration >= min_duration_seconds:
        # Show all movies in the playlist starting from current
        movies_to_include = list(scheduler.movies)
    else:
        # Playlist is < 24 hours, cycle through until we reach 24 hours
        movies_to_include = []
        total_so_far = 0
        all_movies = list(scheduler.movies)
        
        while total_so_far < min_duration_seconds:
            for movie in all_movies:
                movies_to_include.append(movie)
                total_so_far += movie.duration
                if total_so_far >= min_duration_seconds:
                    break

    # Find current movie index to rotate the list
    try:
        current_idx = scheduler.movies.index(current.movie)
    except ValueError:
        current_idx = 0

    # Rotate movies to start from current
    rotated_movies = movies_to_include[current_idx:] + movies_to_include[:current_idx]

    # Generate program entries using FIXED epoch timetable
    # Calculate the uptime from epoch
    uptime = (now.timestamp() - scheduler.epoch) % scheduler.total_duration
    
    # Calculate offset to the start of current movie
    current_offset = sum(m.duration for m in scheduler.movies[:current_idx])
    cycle_start_time = datetime.fromtimestamp(
        scheduler.epoch + int((now.timestamp() - scheduler.epoch) / scheduler.total_duration) * scheduler.total_duration,
        timezone.utc
    )

    # Generate entries with fixed times based on epoch
    current_program_time = cycle_start_time + timedelta(seconds=current_offset)
    
    for movie in rotated_movies:
        start_time = current_program_time
        end_time_prog = start_time + timedelta(seconds=movie.duration)

        # Format times for XMLTV (YYYYMMDDHHMMSS +timezone)
        start_str = start_time.strftime('%Y%m%d%H%M%S')
        tz_offset = '+0000'  # UTC
        end_str = end_time_prog.strftime('%Y%m%d%H%M%S')

        # Generate program entry
        lines.append(f'  <programme start="{start_str} {tz_offset}" '
                    f'stop="{end_str} {tz_offset}" channel="mtv">')
        lines.append(f'    <title lang="en">{_escape_xml(movie.title)}</title>')
        lines.append('  </programme>')

        # Move to next program
        current_program_time = end_time_prog

    lines.append('</tv>')

    return '\n'.join(lines)


def _escape_xml(text: str) -> str:
    """Escape special XML characters"""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))
