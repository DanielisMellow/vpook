"""Synthetic audio provider that simulates talking and idle cycles for testing."""

from __future__ import annotations

import math
import time

from vpook.audio.base import AudioProvider
from vpook.models import AudioLevel


class FakeAudioProvider(AudioProvider):
    """Deterministic audio provider for local development.

    The provider cycles through idle, talking, and transition phases to make
    the overlay visibly animate without requiring a real audio backend.
    """

    _IDLE_SECONDS = 2.0
    _TALKING_SECONDS = 3.0
    _TRANSITION_SECONDS = 1.0
    _CYCLE_SECONDS = _IDLE_SECONDS + _TALKING_SECONDS + _TRANSITION_SECONDS

    def __init__(self) -> None:
        """Initialize the fake provider."""
        super().__init__()
        self._started_at: float | None = None
        self._last_phase: str | None = None
        self._logger.debug("Initialized fake audio provider.")

    @property
    def name(self) -> str:
        """Return the provider identifier.

        Returns:
            str: Provider name for state payloads.
        """
        return "fake"

    def start(self) -> None:
        """Record the start time and reset phase tracking."""
        self._started_at = time.monotonic()
        self._last_phase = None
        self._logger.info("Started fake audio provider.")

    def stop(self) -> None:
        """Clear the start time and phase tracking."""
        self._started_at = None
        self._last_phase = None
        self._logger.info("Stopped fake audio provider.")

    def read_level(self) -> AudioLevel:
        """Compute a synthetic audio level for the current cycle phase.

        Returns:
            AudioLevel: Synthetic audio level snapshot for the current time.

        Raises:
            RuntimeError: If the provider has not been started yet.
        """
        now = time.monotonic()
        if self._started_at is None:
            self._logger.error("read_level() called before provider start.")
            raise RuntimeError(
                "FakeAudioProvider.start() must be called before read_level()."
            )

        phase = (now - self._started_at) % self._CYCLE_SECONDS
        if phase < self._IDLE_SECONDS:
            volume = 0.015 + 0.01 * math.sin(phase * math.pi * 1.5)
            phase_name = "idle"
        elif phase < self._IDLE_SECONDS + self._TALKING_SECONDS:
            talk_phase = phase - self._IDLE_SECONDS
            pulse = 0.5 + 0.5 * math.sin(talk_phase * math.pi * 3.0)
            volume = 0.16 + 0.34 * pulse
            phase_name = "talking"
        else:
            transition_phase = phase - self._IDLE_SECONDS - self._TALKING_SECONDS
            fade = 1.0 - (transition_phase / self._TRANSITION_SECONDS)
            ripple = 0.5 + 0.5 * math.sin(transition_phase * math.pi * 4.0)
            volume = 0.03 + max(0.0, fade) * 0.09 * ripple
            phase_name = "transition"

        if phase_name != self._last_phase:
            self._last_phase = phase_name
            self._logger.debug("Fake provider entered %s phase.", phase_name)

        return AudioLevel(volume=max(0.0, min(volume, 1.0)), timestamp=now)
