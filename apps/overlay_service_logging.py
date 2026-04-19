"""Logging configuration for the overlay service."""

from __future__ import annotations

import logging


def configure_logging(level_str: str = "INFO") -> None:
    """Configure application-wide logging behavior.

    Args:
        level_str: Logging level name (e.g., "DEBUG", "INFO", "WARNING", "ERROR").
    """
    normalized_level = level_str.upper()
    level = getattr(logging, normalized_level, None)
    if not isinstance(level, int):
        raise ValueError(f"Unsupported log level: {level_str}")

    formatter = logging.Formatter("%(asctime)s [%(name)s] [%(levelname)s] %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(console_handler)
    root.setLevel(level)
