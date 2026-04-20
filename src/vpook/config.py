"""Application configuration dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class AvatarConfig:
    """Paths and talking-state styling for avatar images.

    Attributes:
        idle_image: HTTP path for the idle avatar image.
        talking_image: HTTP path for the talking avatar image.
        talking_glow_color: CSS color used for the talking glow effect.
        talking_glow_intensity: Multiplier applied to the talking glow size.
    """

    idle_image: str = "/assets/pookie/idle.png"
    talking_image: str = "/assets/pookie/talking.png"
    talking_glow_color: str = "rgba(80, 220, 255, 0.9)"
    talking_glow_intensity: float = 1.0


@dataclass(slots=True)
class AppConfig:
    """Top-level runtime configuration for the vpook overlay service.

    Attributes:
        provider: Audio provider name to instantiate.
        audio_device: Optional device-name substring for Windows loopback.
        websocket_host: Local host for the WebSocket state server.
        websocket_port: Local port for the WebSocket state server.
        http_host: Local host for the HTTP overlay server.
        http_port: Local port for the HTTP overlay server.
        tick_ms: Main loop tick interval in milliseconds.
        threshold: Voice activity threshold for talking detection.
        attack_ms: Required time above threshold before switching to talking.
        release_ms: Required time below threshold before switching to idle.
        assets_dir: Filesystem directory that contains user-owned avatar assets.
        avatar: Overlay avatar image configuration.
    """

    provider: str = "fake"
    audio_device: str | None = (
        None  # Loopback device name substring; None = system default
    )
    target_process: str | None = (
        None  # Process name substring for windows-audio-session provider
    )
    websocket_host: str = "127.0.0.1"
    websocket_port: int = 8765
    http_host: str = "127.0.0.1"
    http_port: int = 8000
    tick_ms: int = 50
    threshold: float = 0.08
    attack_ms: int = 120
    release_ms: int = 300
    assets_dir: Path = field(default_factory=lambda: Path("apps/assets"))
    avatar: AvatarConfig = field(default_factory=AvatarConfig)
