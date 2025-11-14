"""Database-specific logger that saves to file for debugging."""

import logging
import os
from pathlib import Path
from datetime import datetime


def get_db_logger(name: str = "database") -> logging.Logger:
    """
    Get a database logger that logs to both console and file.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(f"database.{name}")
    
    # Don't add handlers if they already exist (prevents duplicate logs)
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        # Verify it was created
        if not log_dir.exists():
            raise OSError(f"Failed to create logs directory: {log_dir}")
    except Exception as e:
        # If we can't create logs directory, still create logger but only to console
        print(f"⚠ Warning: Could not create logs directory {log_dir}: {e}")
        # Continue without file handler
    
    # File handler - saves to logs/database_YYYY-MM-DD.log
    # Only add file handler if logs directory exists
    if log_dir.exists():
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = log_dir / f"database_{date_str}.log"
        
        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            # Log that file handler was created
            logger.debug(f"Log file handler created: {log_file}")
        except Exception as e:
            print(f"⚠ Warning: Could not create log file {log_file}: {e}")
    
    # Console handler - only shows INFO and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger (avoids duplicate logs)
    logger.propagate = False
    
    return logger

