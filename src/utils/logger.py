"""Logger configuration."""
import logging
import sys
from pythonjsonlogger import jsonlogger
from src.utils.config import config


def setup_logger(name: str) -> logging.Logger:
    """
    Setup JSON logger for Lambda functions.
    
    Args:
        name: Logger name
    
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger
