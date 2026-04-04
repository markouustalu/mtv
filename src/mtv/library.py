"""Library management for movies"""

import random
import logging
from typing import List, Optional

from mtv.models.movie import Movie

logger = logging.getLogger(__name__)


class Library:
    """Manages the movie library in memory"""
    
    def __init__(self):
        self.movies: List[Movie] = []
        self.shuffled_order: List[Movie] = []
        self._shuffled = False
    
    def load_movies(self, movies: List[Movie]) -> None:
        """
        Load movies into the library and shuffle them.
        
        Args:
            movies: List of Movie objects from scanner
        """
        self.movies = movies
        self.shuffle()
        logger.info(f"Library loaded with {len(self.movies)} movies")
    
    def shuffle(self) -> None:
        """Shuffle movie order"""
        self.shuffled_order = self.movies.copy()
        random.shuffle(self.shuffled_order)
        self._shuffled = True
        logger.info("Movies shuffled")
    
    def get_playlist(self) -> List[Movie]:
        """
        Get the current shuffled playlist.
        
        Returns:
            List of movies in play order
        """
        if not self._shuffled and self.movies:
            self.shuffle()
        return self.shuffled_order
    
    def get_total_duration(self) -> float:
        """
        Get total duration of all movies in playlist.
        
        Returns:
            Total duration in seconds
        """
        return sum(movie.duration for movie in self.shuffled_order)
    
    def get_movie_by_path(self, path: str) -> Optional[Movie]:
        """
        Find a movie by its file path.
        
        Args:
            path: File path to search for
            
        Returns:
            Movie object or None
        """
        for movie in self.movies:
            if movie.path == path:
                return movie
        return None
    
    def __len__(self) -> int:
        return len(self.movies)
    
    def __bool__(self) -> bool:
        return bool(self.movies)
