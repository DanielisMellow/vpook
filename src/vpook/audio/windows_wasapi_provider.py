"""WASAPI loopback audio provider for Windows."""

from __future__ import annotations

import time
from collections import deque

import numpy as np
import pyaudiowpatch as pyaudio

from vpook.audio.base import AudioProvider
from vpook.models import AudioLevel

# Number of recent RMS frames to smooth over (~80ms at 50ms tick)
_SMOOTH_WINDOW = 3


class WindowsWasapiProvider(AudioProvider):
    """Captures system audio output via WASAPI loopback.

    Reads whatever is playing through the default output device (speakers/
    headphones), computes RMS volume, and returns it as a normalised [0, 1]
    AudioLevel. Works with Discord, any VOIP app, or any other audio source
    without being tied to a specific service.
    """

    def __init__(self, device_name: str | None = None) -> None:
        """Initialize the Windows WASAPI loopback provider.

        Args:
            device_name: Substring to match against WASAPI loopback device
                names. If None, the system default output loopback is used.
        """
        super().__init__()
        self._device_name = device_name
        self._pa: pyaudio.PyAudio | None = None
        self._stream: pyaudio.Stream | None = None
        self._channels: int = 1
        self._sample_rate: int = 44100
        self._frames_per_buffer: int = 1024
        # Rolling window for smoothing volume spikes
        self._smooth: deque[float] = deque(maxlen=_SMOOTH_WINDOW)
        self._logger.debug("Initialized Windows WASAPI loopback provider.")

    @property
    def name(self) -> str:
        """Return the provider identifier.

        Returns:
            str: Provider name for state payloads.
        """
        return "windows-wasapi"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Open the WASAPI loopback stream on the selected device.

        Raises:
            RuntimeError: If audio APIs or devices are unavailable.
        """
        self._pa = pyaudio.PyAudio()
        device_info = self._find_loopback_device()
        self._channels = min(device_info["maxInputChannels"], 2)
        self._sample_rate = int(device_info["defaultSampleRate"])
        self._logger.info(
            "Opening WASAPI loopback on '%s' (index=%s, %sch @ %sHz).",
            device_info["name"],
            device_info["index"],
            self._channels,
            self._sample_rate,
        )
        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=self._channels,
            rate=self._sample_rate,
            input=True,
            input_device_index=device_info["index"],
            frames_per_buffer=self._frames_per_buffer,
        )

    def stop(self) -> None:
        """Stop and close the WASAPI stream, then terminate PyAudio."""
        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        if self._pa is not None:
            self._pa.terminate()
            self._pa = None
        self._logger.debug("Windows WASAPI loopback provider stopped.")

    # ------------------------------------------------------------------
    # Audio read
    # ------------------------------------------------------------------

    def read_level(self) -> AudioLevel:
        """Read a buffer from the stream and return a smoothed RMS level.

        Returns:
            AudioLevel: Smoothed RMS audio level snapshot.

        Raises:
            RuntimeError: If the provider has not been started.
        """
        if self._stream is None:
            raise RuntimeError("Provider not started. Call start() first.")

        raw = self._stream.read(self._frames_per_buffer, exception_on_overflow=False)
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)

        # RMS normalised to [0, 1] (int16 max = 32768)
        rms = float(np.sqrt(np.mean(samples**2))) / 32768.0

        # Light smoothing so animation doesn't strobe on transients
        self._smooth.append(rms)
        smoothed = float(np.mean(self._smooth))

        return AudioLevel(volume=min(smoothed, 1.0), timestamp=time.monotonic())

    # ------------------------------------------------------------------
    # Device discovery
    # ------------------------------------------------------------------

    def _find_loopback_device(self) -> dict:
        if self._pa is None:
            raise RuntimeError("Provider not started. Call start() first.")

        try:
            wasapi_api = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError as exc:
            raise RuntimeError(
                "WASAPI host API not available. Ensure you are on Windows and "
                "that audio drivers support WASAPI."
            ) from exc

        # Collect all WASAPI loopback devices
        loopbacks = list(self._pa.get_loopback_device_info_generator())
        if not loopbacks:
            raise RuntimeError("No WASAPI loopback devices found.")

        # If the caller named a specific device, match by substring
        if self._device_name is not None:
            needle = self._device_name.lower()
            matches = [d for d in loopbacks if needle in d["name"].lower()]
            if not matches:
                available = [d["name"] for d in loopbacks]
                raise RuntimeError(
                    f"No loopback device matching '{self._device_name}'. "
                    f"Available: {available}"
                )
            self._logger.debug("Matched loopback device: %s", matches[0]["name"])
            return matches[0]

        # Default: use the loopback that mirrors the default output device
        default_out_index = wasapi_api["defaultOutputDevice"]
        default_out = self._pa.get_device_info_by_index(default_out_index)
        default_name = default_out["name"].lower()

        for device in loopbacks:
            if default_name in device["name"].lower():
                self._logger.debug("Using default output loopback: %s", device["name"])
                return device

        # Fallback: first available loopback
        self._logger.warning(
            "Could not match default output '%s' to a loopback device. "
            "Falling back to first available: %s",
            default_out["name"],
            loopbacks[0]["name"],
        )
        return loopbacks[0]
