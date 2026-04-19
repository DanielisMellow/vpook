"""Voice activity detection with attack and release timing."""

from __future__ import annotations

import logging
from dataclasses import dataclass


@dataclass(slots=True)
class VoiceStateSnapshot:
    """Immutable snapshot of the voice-activity detector output.

    Attributes:
        talking: Whether the detector currently considers the user talking.
        volume: Most recent normalized volume sample.
        timestamp: Monotonic timestamp for the sample.
    """

    talking: bool
    volume: float
    timestamp: float


class VoiceActivityDetector:
    """Detect voice activity using threshold-based attack and release logic."""

    def __init__(self, threshold: float, attack_ms: int, release_ms: int) -> None:
        """Initialize the detector.

        Args:
            threshold: Volume threshold above which speech may begin.
            attack_ms: Time the signal must remain above threshold before
                switching to talking.
            release_ms: Time the signal must remain below threshold before
                switching to idle.
        """
        self._logger = logging.getLogger(__name__)
        self.threshold = threshold
        self.attack_seconds = attack_ms / 1000.0
        self.release_seconds = release_ms / 1000.0
        self._talking = False
        self._above_since: float | None = None
        self._below_since: float | None = None
        self._logger.debug(
            "Initialized voice activity detector with "
            "threshold=%s attack_ms=%s release_ms=%s.",
            threshold,
            attack_ms,
            release_ms,
        )

    def update(self, volume: float, now: float) -> VoiceStateSnapshot:
        """Update detector state with a new volume sample.

        Args:
            volume: Normalized volume sample to evaluate.
            now: Monotonic timestamp associated with the sample.

        Returns:
            VoiceStateSnapshot: Current detector output after processing the
            sample.
        """
        if volume >= self.threshold:
            self._below_since = None
            if self._above_since is None:
                self._above_since = now
                self._logger.debug("Volume crossed threshold: volume=%.3f.", volume)
            if not self._talking and now - self._above_since >= self.attack_seconds:
                self._talking = True
                self._logger.info(
                    "Voice state changed to talking at volume %.3f.", volume
                )
        else:
            self._above_since = None
            if self._below_since is None:
                self._below_since = now
                self._logger.debug(
                    "Volume dropped below threshold: volume=%.3f.", volume
                )
            if self._talking and now - self._below_since >= self.release_seconds:
                self._talking = False
                self._logger.info("Voice state changed to idle at volume %.3f.", volume)

        return VoiceStateSnapshot(talking=self._talking, volume=volume, timestamp=now)
