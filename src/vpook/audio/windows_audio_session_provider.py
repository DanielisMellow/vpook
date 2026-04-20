"""Windows Audio Session API provider for per-application volume monitoring."""

from __future__ import annotations

import time
from collections import deque

from vpook.audio.base import AudioProvider
from vpook.models import AudioLevel

# Rolling window for smoothing (matches the WASAPI loopback provider)
_SMOOTH_WINDOW = 3
# Re-enumerate sessions every N seconds to pick up app restarts
_SESSION_REFRESH_INTERVAL = 5.0


class WindowsAudioSessionProvider(AudioProvider):
    """Monitors a specific application's audio via Windows Audio Session API.

    Uses IAudioMeterInformation to read the peak volume level of the target
    process's audio session(s) without capturing the raw audio stream. This
    isolates one application's audio from all other system output — no virtual
    audio cables or full-device loopback required.

    Supports multiple concurrent sessions for the same process name (e.g.
    Discord spawns several processes) by taking the max peak across all of
    them.

    Requires Windows Vista+ and the pycaw package.
    """

    def __init__(self, process_name: str = "discord") -> None:
        """Initialize the Windows Audio Session provider.

        Args:
            process_name: Case-insensitive substring to match against running
                process names. The first matching audio session(s) are used.
        """
        super().__init__()
        self._process_name = process_name.lower()
        self._meters: list = []
        self._last_refresh: float = 0.0
        self._smooth: deque[float] = deque(maxlen=_SMOOTH_WINDOW)
        self._started = False

    @property
    def name(self) -> str:
        """Return the provider identifier.

        Returns:
            str: Provider name for state payloads.
        """
        return "windows-audio-session"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Enumerate audio sessions and locate the target process.

        Raises:
            ImportError: If pycaw is not installed.
        """
        self.stop()
        self._smooth.clear()
        self._refresh_sessions()
        self._started = True
        self._logger.info(
            "Windows Audio Session provider started, targeting process '%s'.",
            self._process_name,
        )

    def stop(self) -> None:
        """Release session references."""
        self._meters.clear()
        self._smooth.clear()
        self._last_refresh = 0.0
        self._started = False
        self._logger.debug("Windows Audio Session provider stopped.")

    # ------------------------------------------------------------------
    # Audio read
    # ------------------------------------------------------------------

    def read_level(self) -> AudioLevel:
        """Read the peak volume across all matching process audio sessions.

        Automatically refreshes session list on the configured interval so the
        provider recovers if the target application is restarted.

        Returns:
            AudioLevel: Smoothed peak audio level snapshot. Returns 0.0 volume
                when the target process has no active audio session.
        """
        if not self._started:
            raise RuntimeError("Provider not started. Call start() first.")

        now = time.monotonic()
        if now - self._last_refresh > _SESSION_REFRESH_INTERVAL:
            self._refresh_sessions()

        peak = 0.0
        dead: list[int] = []

        for i, meter in enumerate(self._meters):
            try:
                peak = max(peak, meter.GetPeakValue())
            except Exception:  # noqa: BLE001
                # Session was closed (app exited, device changed, etc.)
                dead.append(i)

        for i in reversed(dead):
            self._meters.pop(i)

        self._smooth.append(peak)
        smoothed = float(sum(self._smooth) / len(self._smooth))
        return AudioLevel(volume=min(smoothed, 1.0), timestamp=now)

    # ------------------------------------------------------------------
    # Session discovery
    # ------------------------------------------------------------------

    def _refresh_sessions(self) -> None:
        """Re-enumerate Windows audio sessions and update meter references."""
        from pycaw.pycaw import AudioUtilities, IAudioMeterInformation  # noqa: PLC0415

        self._last_refresh = time.monotonic()

        try:
            sessions = AudioUtilities.GetAllSessions()
        except Exception as exc:  # noqa: BLE001
            self._logger.warning("Failed to enumerate audio sessions: %s", exc)
            return

        # Only replace meters after a successful enumeration so a transient
        # COM error does not silently zero out an otherwise healthy session.
        new_meters: list = []

        for session in sessions:
            if session.Process is None:
                continue
            try:
                proc_name = session.Process.name().lower()
            except Exception as exc:  # noqa: BLE001
                self._logger.debug(
                    "Skipping audio session with unreadable process name: %s",
                    exc,
                )
                continue

            if self._process_name not in proc_name:
                continue

            try:
                meter = session._ctl.QueryInterface(IAudioMeterInformation)
                # Probe the interface before storing it
                meter.GetPeakValue()
                new_meters.append(meter)
                self._logger.debug(
                    "Tracking audio session: process='%s' pid=%s.",
                    session.Process.name(),
                    session.Process.pid,
                )
            except Exception as exc:  # noqa: BLE001
                self._logger.debug(
                    "Skipping session for '%s': %s", proc_name, exc
                )

        self._meters = new_meters

        if not self._meters:
            self._logger.warning(
                "No active audio sessions found for process '%s'. "
                "Is the application running and outputting audio?",
                self._process_name,
            )
        else:
            self._logger.info(
                "Tracking %d audio session(s) for process '%s'.",
                len(self._meters),
                self._process_name,
            )
