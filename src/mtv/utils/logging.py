"""Logging configuration for MTV"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from mtv.config import LoggingConfig


def setup_logging(config: LoggingConfig) -> logging.Logger:
    """
    Setup application logging.
    
    Args:
        config: Logging configuration
        
    Returns:
        Root logger instance
    """
    # Get root logger
    logger = logging.getLogger('mtv')
    logger.setLevel(getattr(logging, config.level.upper()))
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)-8s] %(name)s %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    try:
        log_path = Path(config.file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            config.file,
            maxBytes=config.max_size_mb * 1024 * 1024,
            backupCount=config.backup_count
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logging.warning(f"Could not setup file logging: {e}")
    
    return logger
