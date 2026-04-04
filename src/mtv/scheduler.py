"""Scheduler with fixed epoch timetable algorithm"""

import logging
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Optional

from mtv.models.movie import Movie
from mtv.config import Config

logger = logging.getLogger(__name__)


@dataclass
class PlaybackInfo:
    """Information about current playback position"""
    movie: Movie
    seek_time: float  # Position in movie to start streaming (seconds)
    progress: float   # Progress through current movie (0.0 to 1.0)
    cycle_number: int  # Which cycle through the playlist we're on


class Scheduler:
    """
    Manages the timetable for movie playback.
    
    Uses a fixed epoch approach so that the playlist position
    is deterministic regardless of server restarts.
    """
    
    def __init__(self, movies: List[Movie], config: Config):
        self.movies = movies  # Shuffled playlist
        self.config = config
        self.epoch = config.timetable.epoch
        self.total_duration = sum(m.duration for m in movies)
        
        logger.info(f"Scheduler initialized with {len(movies)} movies")
        logger.info(f"Total playlist duration: {self._format_duration(self.total_duration)}")
        logger.info(f"Timetable epoch: {datetime.fromtimestamp(self.epoch, timezone.utc)}")
    
    def get_current_playback(self, request_time: Optional[datetime] = None) -> PlaybackInfo:
        """
        Calculate which movie should be playing and at what position.
        
        Uses fixed epoch: position = (now - epoch) MOD total_duration
        
        Args:
            request_time: Time to calculate for (defaults to now)
            
        Returns:
            PlaybackInfo with movie, seek position, and progress
        """
        if request_time is None:
            request_time = datetime.now(timezone.utc)
        
        # Calculate uptime from fixed epoch
        uptime = (request_time.timestamp() - self.epoch) % self.total_duration
        
        # Find which movie and offset
        current_offset = 0
        cycle_number = int((request_time.timestamp() - self.epoch) / self.total_duration)
        
        for movie in self.movies:
            if current_offset + movie.duration > uptime:
                # This is the current movie
                seek_time = uptime - current_offset
                progress = seek_time / movie.duration if movie.duration > 0 else 0
                
                logger.debug(
                    f"Current playback: {movie.filename} "
                    f"at {self._format_duration(seek_time)} "
                    f"(cycle {cycle_number})"
                )
                
                return PlaybackInfo(
                    movie=movie,
                    seek_time=seek_time,
                    progress=progress,
                    cycle_number=cycle_number
                )
            current_offset += movie.duration
        
        # Edge case: exactly at boundary, return last movie near end
        last_movie = self.movies[-1]
        return PlaybackInfo(
            movie=last_movie,
            seek_time=last_movie.duration - 1.0,
            progress=0.99,
            cycle_number=cycle_number
        )
    
    def get_next_movies(self, count: int = 3) -> List[Movie]:
        """
        Get the next N movies in the playlist.
        
        Args:
            count: Number of upcoming movies to return
            
        Returns:
            List of upcoming movies
        """
        # Find current index
        current = self.get_current_playback()
        try:
            current_idx = self.movies.index(current.movie)
        except ValueError:
            current_idx = 0
        
        # Get next movies (wrapping around)
        next_movies = []
        for i in range(1, count + 1):
            next_idx = (current_idx + i) % len(self.movies)
            next_movies.append(self.movies[next_idx])
        
        return next_movies
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration as HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def get_program_start_time(self, movie: Movie, cycle: int = 0) -> datetime:
        """
        Calculate when a specific movie starts in a given cycle.
        
        Args:
            movie: The movie to find start time for
            cycle: Which cycle (0 = current, 1 = next, etc.)
            
        Returns:
            datetime when this movie starts
        """
        try:
            movie_idx = self.movies.index(movie)
        except ValueError:
            raise ValueError(f"Movie {movie.filename} not in playlist")
        
        # Calculate offset within playlist
        offset = sum(m.duration for m in self.movies[:movie_idx])
        
        # Calculate absolute time
        start_timestamp = self.epoch + (cycle * self.total_duration) + offset
        
        return datetime.fromtimestamp(start_timestamp, timezone.utc)
