"""XMLTV EPG generation"""

from datetime import datetime, timezone, timedelta
from typing import List

from mtv.library import Library
from mtv.scheduler import Scheduler
from mtv.config import Config


def generate_epg(library: Library, scheduler: Scheduler, config: Config) -> str:
    """
    Generate XMLTV EPG data.
    
    Generates 7 days of program data based on the timetable.
    
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
    
    # Channel definition
    lines.append('  <channel id="marko-tv">')
    lines.append('    <display-name>Marko TV</display-name>')
    lines.append('  </channel>')
    
    # Generate programs for next 7 days
    now = datetime.now(timezone.utc)
    end_time = now + timedelta(days=7)
    
    # Start from current position
    current_time = now
    cycle = 0
    
    while current_time < end_time:
        for movie in scheduler.movies:
            # Calculate program start and end times
            start_time = scheduler.get_program_start_time(movie, cycle)
            end_time_prog = start_time + timedelta(seconds=movie.duration)
            
            # Skip if already past end date
            if start_time >= end_time:
                break
            
            # Format times for XMLTV (YYYYMMDDHHMMSS +timezone)
            start_str = start_time.strftime('%Y%m%d%H%M%S')
            tz_offset = '+0000'  # UTC
            end_str = end_time_prog.strftime('%Y%m%d%H%M%S')
            
            # Generate program entry
            lines.append(f'  <programme start="{start_str} {tz_offset}" '
                        f'stop="{end_str} {tz_offset}" channel="marko-tv">')
            lines.append(f'    <title lang="en">{_escape_xml(movie.title)}</title>')
            lines.append(f'    <desc lang="en">{_escape_xml(_get_description(movie))}</desc>')
            
            # Add category based on video codec (hacky but works)
            lines.append('    <category lang="en">Movie</category>')
            
            # Add rating (placeholder - could be extracted from metadata)
            lines.append('    <rating>')
            lines.append('      <value>NR</value>')
            lines.append('    </rating>')
            
            lines.append('  </programme>')
            
            # Move to next program
            current_time = end_time_prog
        
        cycle += 1
    
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


def _get_description(movie) -> str:
    """Generate a description for a movie"""
    # In a real implementation, this could fetch from TMDB or similar
    # For now, use filename-based info
    resolution = f"{movie.width}x{movie.height}"
    video_codec = movie.video_codec
    
    audio_info = []
    for stream in movie.audio_streams:
        lang = stream.language or 'und'
        audio_info.append(f"{stream.codec} ({lang})")
    
    subtitle_info = []
    if movie.external_subtitle:
        subtitle_info.append("External subtitles")
    
    desc_parts = [
        f"Video: {video_codec} {resolution}",
        f"Audio: {', '.join(audio_info)}",
    ]
    if subtitle_info:
        desc_parts.append(f"Subtitles: {', '.join(subtitle_info)}")
    
    return '. '.join(desc_parts)
