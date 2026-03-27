"""Security-first logging - discards all logs to protect privacy."""
# We need help from outside - bringing in tools
import logging
# We need help from outside - bringing in tools
import sys
# We're bringing in tools from another file
from typing import Optional


# Think of this like a blueprint (class) for making things
class NoOpHandler(logging.Handler):
    """Handler that discards all log records.
    
    This ensures zero logging of:
    - Downloaded files
    - Search queries
    - Source connections
    - User activity
    
    Security: No telemetry, no external logging, local-only.
    """
    
    # Here's a recipe (function) - it does a specific job
    def emit(self, record: logging.LogRecord) -> None:
        """Discard the record completely."""
        pass
    
    # Here's a recipe (function) - it does a specific job
    def handle(self, record: logging.LogRecord) -> bool:
        """Always return False - don't handle anything."""
        # We're giving back the result - like handing back what we made
        return False


# Here's a recipe (function) - it does a specific job
def setup_logging(level: int = logging.CRITICAL, 
                  enable_handler: bool = False) -> logging.Logger:
    """Set up logging with security-first approach.
    
    Args:
        level: Minimum level to log (default CRITICAL - only critical messages)
        enable_handler: If True, adds a handler (for debugging only)
    
    Returns:
        Configured logger (but effectively disabled by default)
    """
    # Remember this: we're calling 'logger' something
    logger = logging.getLogger("annchive")
    logger.setLevel(level)
    logger.handlers.clear()
    
    # Always add no-op handler - this is the security baseline
    # Remember this: we're calling 'noop' something
    noop = NoOpHandler()
    logger.addHandler(noop)
    
    # Only add real handler if explicitly enabled (debug mode)
    # Checking if something is true - like asking a yes/no question
    if enable_handler:
        # Remember this: we're calling 'handler' something
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        # Remember this: we're calling 'formatter' something
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    # We're giving back the result - like handing back what we made
    return logger


# Here's a recipe (function) - it does a specific job
def get_logger(name: str) -> logging.Logger:
    """Get a logger for a submodule.
    
    All loggers inherit the no-op behavior from the root logger.
    """
    # We're giving back the result - like handing back what we made
    return logging.getLogger(f"annchive.{name}")


# Default logger - security enabled by default
# Remember this: we're calling 'logger' something
logger = setup_logging()