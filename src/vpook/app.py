"""Application entry point and main run loop for vpook."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from vpook.audio.base import AudioProvider
from vpook.audio.fake_provider import FakeAudioProvider
from vpook.config import AppConfig
from vpook.models import OverlayState
from vpook.state.voice_state import VoiceActivityDetector
from vpook.transport.static_server import StaticServer
from vpook.transport.websocket_server import WebSocketStateServer

LOGGER = logging.getLogger(__name__)


def create_audio_provider(config: AppConfig) -> AudioProvider:
    """Create the configured audio provider.

    Args:
        config: Application configuration that selects the provider backend.

    Returns:
        AudioProvider: The provider instance requested by the configuration.

    Raises:
        ValueError: If the configured provider name is not supported.
    """
    LOGGER.debug("Creating audio provider for provider=%s.", config.provider)
    if config.provider == "fake":
        return FakeAudioProvider()
    if config.provider == "windows-wasapi":
        from vpook.audio.windows_wasapi_provider import (  # noqa: PLC0415
            WindowsWasapiProvider,
        )

        return WindowsWasapiProvider(device_name=config.audio_device)
    LOGGER.error("Unsupported audio provider requested: %s", config.provider)
    raise ValueError(f"Unsupported audio provider: {config.provider}")


async def run(config: AppConfig | None = None) -> None:
    """Run the vpook service until interrupted.

    Args:
        config: Optional runtime configuration. If omitted, defaults are used.
    """
    app_config = config or AppConfig()
    LOGGER.info(
        "Starting vpook with provider=%s http=%s:%s websocket=%s:%s tick_ms=%s.",
        app_config.provider,
        app_config.http_host,
        app_config.http_port,
        app_config.websocket_host,
        app_config.websocket_port,
        app_config.tick_ms,
    )
    provider = create_audio_provider(app_config)
    detector = VoiceActivityDetector(
        threshold=app_config.threshold,
        attack_ms=app_config.attack_ms,
        release_ms=app_config.release_ms,
    )
    websocket_server = WebSocketStateServer(
        app_config.websocket_host, app_config.websocket_port
    )
    static_server = StaticServer(app_config)
    tick_seconds = app_config.tick_ms / 1000.0

    provider.start()
    await websocket_server.start()
    static_server.start()

    try:
        last_talking: bool | None = None
        while True:
            level = provider.read_level()
            snapshot = detector.update(level.volume, level.timestamp)
            state = OverlayState(
                talking=snapshot.talking,
                volume=snapshot.volume,
                source=provider.name,
            )
            if state.talking != last_talking:
                last_talking = state.talking
                LOGGER.debug(
                    "Overlay state updated: talking=%s volume=%.3f source=%s.",
                    state.talking,
                    state.volume,
                    state.source,
                )
            await websocket_server.broadcast(state)
            await asyncio.sleep(tick_seconds)
    finally:
        LOGGER.info("Shutting down vpook services.")
        provider.stop()
        static_server.stop()
        await websocket_server.stop()
        LOGGER.info("vpook shutdown complete.")


def main(config: AppConfig | None = None) -> None:
    """Run the application event loop.

    Args:
        config: Optional runtime configuration. If omitted, defaults are used.
    """
    with suppress(KeyboardInterrupt):
        asyncio.run(run(config))
