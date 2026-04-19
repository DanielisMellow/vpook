"""Shared data models used across vpook."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class AudioLevel:
    """Instantaneous audio level sample from a provider.

    Attributes:
        volume: Normalized audio level in the range ``0.0`` to ``1.0``.
        timestamp: Monotonic timestamp when the sample was captured.
    """

    volume: float
    timestamp: float


@dataclass(slots=True)
class OverlayState:
    """Current voice-activity state broadcast to overlay clients.

    Attributes:
        talking: Whether the detector currently considers the user talking.
        volume: Most recent normalized volume sample.
        source: Provider identifier that produced the state.
    """

    talking: bool
    volume: float
    source: str

    def to_payload(self) -> dict[str, object]:
        """Serialize the state for WebSocket delivery.

        Returns:
            dict[str, object]: JSON-serializable state payload including the
            message type.
        """
        payload = asdict(self)
        payload["type"] = "state"
        return payload


@dataclass(slots=True)
class AvatarConfig:
    """Avatar image paths used in the overlay config payload.

    Attributes:
        idle_image: HTTP path to the idle avatar image.
        talking_image: HTTP path to the talking avatar image.
    """

    idle_image: str
    talking_image: str


@dataclass(slots=True)
class OverlayConfigPayload:
    """Overlay bootstrap payload served to clients.

    Attributes:
        websocket_url: WebSocket URL used for live overlay state.
        avatar: Avatar image configuration for the overlay client.
    """

    websocket_url: str
    avatar: AvatarConfig
