"""Abstract base class for audio providers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from vpook.models import AudioLevel


class AudioProvider(ABC):
    """Abstract interface for audio capture backends."""

    def __init__(self) -> None:
        """Initialize shared provider state."""
        self._logger = logging.getLogger(__name__)

    @property
    @abstractmethod
    def name(self) -> str:
        """Return a short identifier for this provider.

        Returns:
            str: Stable provider name used in overlay state payloads.
        """
        raise NotImplementedError

    @abstractmethod
    def start(self) -> None:
        """Open the audio stream and begin capturing."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Close the audio stream and release resources."""
        raise NotImplementedError

    @abstractmethod
    def read_level(self) -> AudioLevel:
        """Read the current audio level.

        Returns:
            AudioLevel: Current audio level snapshot from the provider.
        """
        raise NotImplementedError
