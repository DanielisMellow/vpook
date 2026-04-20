"""Configurable entry point for the overlay service."""

from __future__ import annotations

from overlay_service_logging import configure_logging
from vpook.app import main
from vpook.config import AppConfig

# Global logging level for the app process.
LOG_LEVEL = "INFO"

# ---------------------------------------------------------------------------
# Audio provider selection — set exactly one of these to True.
# ---------------------------------------------------------------------------

# Fake sine-wave oscillator. Use for development and tests.
USE_FAKE_AUDIO = True

# Capture everything coming out of a specific output device (full mix).
# Useful if you want all system audio, not just one app.
USE_DEVICE_LOOPBACK = False

# Capture only a specific application's audio session via the Windows Audio
# Session API. No virtual audio cables needed — the OS meters each app
# individually. Set USE_PROCESS_AUDIO = True and name the target process.
USE_PROCESS_AUDIO = False

# ---------------------------------------------------------------------------
# Provider-specific settings
# ---------------------------------------------------------------------------

# (USE_DEVICE_LOOPBACK) Substring to match the output device name.
# Leave as None to use the system default output loopback device.
WINDOWS_LOOPBACK_DEVICE_NAME: str | None = None

# (USE_PROCESS_AUDIO) Case-insensitive substring of the target process name.
# Discord spawns several processes — any one that outputs audio will be found.
TARGET_PROCESS: str = "discord"


def build_config() -> AppConfig:
    """Build the app configuration from top-level module settings."""
    if USE_PROCESS_AUDIO:
        return AppConfig(
            provider="windows-audio-session",
            target_process=TARGET_PROCESS,
        )
    if USE_DEVICE_LOOPBACK:
        return AppConfig(
            provider="windows-wasapi",
            audio_device=WINDOWS_LOOPBACK_DEVICE_NAME,
        )
    return AppConfig(provider="fake")


if __name__ == "__main__":
    configure_logging(LOG_LEVEL)
    main(build_config())
