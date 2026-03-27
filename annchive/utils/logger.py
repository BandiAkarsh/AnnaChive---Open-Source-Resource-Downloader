"""Security-first logging - discards all logs to protect privacy."""
import logging
import sys
from typing import Optional


class NoOpHandler(logging.Handler):
    """Handler that discards all log records.
    
    This ensures zero logging of:
    - Downloaded files
    - Search queries
    - Source connections
    - User activity
    
    Security: No telemetry, no external logging, local-only.
    """
    
    def emit(self, record: logging.LogRecord) -> None:
        """Discard the record completely."""
        pass
    
    def handle(self, record: logging.LogRecord) -> bool:
        """Always return False - don't handle anything."""
        return False


def setup_logging(level: int = logging.CRITICAL, 
                  enable_handler: bool = False) -> logging.Logger:
    """Set up logging with security-first approach.
    
    Args:
        level: Minimum level to log (default CRITICAL - only critical messages)
        enable_handler: If True, adds a handler (for debugging only)
    
    Returns:
        Configured logger (but effectively disabled by default)
    """
    logger = logging.getLogger("annchive")
    logger.setLevel(level)
    logger.handlers.clear()
    
    # Always add no-op handler - this is the security baseline
    noop = NoOpHandler()
    logger.addHandler(noop)
    
    # Only add real handler if explicitly enabled (debug mode)
    if enable_handler:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a submodule.
    
    All loggers inherit the no-op behavior from the root logger.
    """
    return logging.getLogger(f"annchive.{name}")


# Default logger - security enabled by default
logger = setup_logging()