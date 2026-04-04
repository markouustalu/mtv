"""M3U playlist generation for Kodi"""

from typing import Optional

from mtv.library import Library
from mtv.config import Config


def generate_m3u(library: Library, config: Config) -> str:
    """
    Generate M3U playlist for Kodi.
    
    Uses inputstream.ffmpegdirect for direct MKV streaming.
    
    Args:
        library: Movie library
        config: Application configuration
        
    Returns:
        M3U playlist content as string
    """
    lines = []
    
    # M3U header
    lines.append("#EXTM3U")
    
    # Get server URL
    server_url = f"http://{config.server.host}:{config.server.port}"
    
    # Single channel entry
    lines.append('#EXTINF:-1,tgroup="Marko TV",Marko TV')
    lines.append('#KODIPROP:inputstream=inputstream.ffmpegdirect')
    lines.append('#KODIPROP:mimetype=video/x-matroska')
    lines.append('#KODIPROP:inputstream.ffmpegdirect.open_mode=ffmpeg')
    lines.append(f'{server_url}/stream/')
    
    return '\n'.join(lines)


def generate_m3u_with_movies(
    library: Library, 
    config: Config,
    include_all: bool = False
) -> str:
    """
    Generate M3U playlist with individual movie entries.
    
    Useful for testing or if you want separate channels per movie.
    
    Args:
        library: Movie library
        config: Application configuration
        include_all: If True, include all movies as separate entries
        
    Returns:
        M3U playlist content as string
    """
    lines = []
    lines.append("#EXTM3U")
    
    server_url = f"http://{config.server.host}:{config.server.port}"
    
    # Main channel (current movie based on timetable)
    lines.append('#EXTINF:-1,tgroup="Marko TV",Marko TV (Live)')
    lines.append('#KODIPROP:inputstream=inputstream.ffmpegdirect')
    lines.append('#KODIPROP:mimetype=video/x-matroska')
    lines.append('#KODIPROP:inputstream.ffmpegdirect.open_mode=ffmpeg')
    lines.append(f'{server_url}/stream/')
    
    # Optional: list all movies as separate entries
    if include_all:
        lines.append('#EXTINF:-1,tgroup="Marko TV",Marko TV - All Movies')
        for movie in library.get_playlist():
            duration_hours = int(movie.duration / 3600)
            duration_mins = int((movie.duration % 3600) / 60)
            title = movie.title
            
            lines.append(f'#EXTINF:{int(movie.duration)},tgroup="Movies",{title}')
            lines.append('#KODIPROP:inputstream=inputstream.ffmpegdirect')
            lines.append('#KODIPROP:mimetype=video/x-matroska')
            lines.append(f'{server_url}/movie/{movie.filename}')
    
    return '\n'.join(lines)
