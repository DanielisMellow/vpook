"""Configurable entry point for the overlay service."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    from overlay_service_logging import configure_logging
except ModuleNotFoundError:  # pragma: no cover - module import path variant
    from apps.overlay_service_logging import configure_logging

from vpook.app import main
from vpook.config import AppConfig

# Global logging level for the app process.
LOG_LEVEL = "INFO"

# Use the fake provider for development or tests. Set to False to capture
# Windows system audio via WASAPI loopback instead.
USE_FAKE_AUDIO = True

# Optional substring match for the Windows output device to mirror. Leave as
# None to use the system default output loopback device.
WINDOWS_LOOPBACK_DEVICE_NAME: str | None = None


def build_config() -> AppConfig:
    """Build the app configuration from top-level module settings."""
    provider = "fake" if USE_FAKE_AUDIO else "windows-wasapi"
    audio_device = None if USE_FAKE_AUDIO else WINDOWS_LOOPBACK_DEVICE_NAME
    return AppConfig(provider=provider, audio_device=audio_device)


if __name__ == "__main__":
    configure_logging(LOG_LEVEL)
    main(build_config())
