import sys
import os
from pathlib import Path
from loguru import logger


def setup_logging(
    log_level: str = "INFO",
    log_file: Path | None = None,
    rotation: str = "10 MB",
    retention: str = "7 days",
) -> None:
    """Configure logging for the pipeline."""
    logger.remove()

    level = log_level.upper()

    # Console handler — human-readable
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File handler — structured for audit trail
    if log_file:
        logger.add(
            str(log_file),
            level="DEBUG",
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
                "{name}:{function}:{line} | {message}"
            ),
            rotation=rotation,
            retention=retention,
            encoding="utf-8",
        )


def get_logger(name: str):
    """Return a bound logger with a component name."""
    return logger.bind(name=name)
