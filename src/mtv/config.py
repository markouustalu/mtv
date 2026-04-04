"""Configuration management for MTV"""

import os
import yaml
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8555


@dataclass
class MediaConfig:
    folder: str = ""
    extensions: List[str] = field(default_factory=lambda: [".mp4", ".mkv"])
    subtitle_extensions: List[str] = field(default_factory=lambda: [".srt", ".sub", ".idx", ".vtt"])
    preferred_languages: dict = field(default_factory=lambda: {"audio": ["en"], "subtitle": ["en"]})
    prefer_english: bool = True


@dataclass
class StreamingConfig:
    timeout: int = 300
    buffer_size: int = 8192


@dataclass
class TimetableConfig:
    epoch: int = 1704067200  # January 1, 2024 00:00:00 UTC


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "logs/mtv.log"
    max_size_mb: int = 10
    backup_count: int = 3


@dataclass
class Config:
    """Main configuration container"""
    server: ServerConfig = field(default_factory=ServerConfig)
    media: MediaConfig = field(default_factory=MediaConfig)
    streaming: StreamingConfig = field(default_factory=StreamingConfig)
    timetable: TimetableConfig = field(default_factory=TimetableConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> 'Config':
        """Load configuration from YAML file with environment variable overrides"""
        # Default config path
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
        
        config_path = Path(config_path)
        
        # Load from YAML
        config_dict = {}
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f) or {}
        
        # Create config object with defaults
        config = cls()
        
        # Update from YAML if present
        if config_dict:
            if 'server' in config_dict:
                config.server = ServerConfig(**config_dict['server'])
            if 'media' in config_dict:
                config.media = MediaConfig(**config_dict['media'])
            if 'streaming' in config_dict:
                config.streaming = StreamingConfig(**config_dict['streaming'])
            if 'timetable' in config_dict:
                config.timetable = TimetableConfig(**config_dict['timetable'])
            if 'logging' in config_dict:
                config.logging = LoggingConfig(**config_dict['logging'])
        
        # Override with environment variables
        config = cls._apply_env_overrides(config)
        
        # Validate
        config.validate()
        
        return config
    
    @classmethod
    def _apply_env_overrides(cls, config: 'Config') -> 'Config':
        """Apply environment variable overrides"""
        # Server
        if env := os.getenv('MTV_SERVER_HOST'):
            config.server.host = env
        if env := os.getenv('MTV_SERVER_PORT'):
            config.server.port = int(env)
        
        # Media
        if env := os.getenv('MTV_MEDIA_FOLDER'):
            config.media.folder = env
        if env := os.getenv('MTV_PREFER_ENGLISH'):
            config.media.prefer_english = env.lower() in ('true', '1', 'yes')
        
        # Streaming
        if env := os.getenv('MTV_STREAMING_TIMEOUT'):
            config.streaming.timeout = int(env)
        if env := os.getenv('MTV_STREAMING_BUFFER_SIZE'):
            config.streaming.buffer_size = int(env)
        
        # Timetable
        if env := os.getenv('MTV_TIMETABLE_EPOCH'):
            config.timetable.epoch = int(env)
        
        # Logging
        if env := os.getenv('MTV_LOG_LEVEL'):
            config.logging.level = env
        
        return config
    
    def validate(self) -> None:
        """Validate configuration"""
        if not self.media.folder:
            raise ValueError("Media folder must be specified")
        
        media_path = Path(self.media.folder)
        if not media_path.exists():
            raise ValueError(f"Media folder does not exist: {self.media.folder}")
        
        if not media_path.is_dir():
            raise ValueError(f"Media path is not a directory: {self.media.folder}")
        
        if not 1 <= self.server.port <= 65535:
            raise ValueError(f"Invalid port number: {self.server.port}")
