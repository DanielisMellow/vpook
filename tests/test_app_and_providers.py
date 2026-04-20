"""Regression tests for provider lifecycle and startup cleanup bugs."""

from __future__ import annotations

import asyncio
import importlib
import math
import sys
import time
from types import ModuleType, SimpleNamespace

import pytest

from vpook.config import AppConfig
from vpook.models import AudioLevel


class _DummyProvider:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    @property
    def name(self) -> str:
        return "dummy"

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def read_level(self) -> AudioLevel:
        return AudioLevel(volume=0.0, timestamp=0.0)


def test_run_stops_started_services_when_static_server_start_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from vpook import app

    provider = _DummyProvider()

    class DummyWebSocketServer:
        def __init__(self, host: str, port: int) -> None:
            self.host = host
            self.port = port
            self.started = False
            self.stopped = False

        async def start(self) -> None:
            self.started = True

        async def stop(self) -> None:
            self.stopped = True

        async def broadcast(self, _state: object) -> None:
            return None

    websocket_server = DummyWebSocketServer("127.0.0.1", 8765)

    class FailingStaticServer:
        def __init__(self, config: AppConfig) -> None:
            self.config = config
            self.started = False

        def start(self) -> None:
            self.started = True
            raise RuntimeError("bind failed")

        def stop(self) -> None:
            raise AssertionError("stop() should not be called when start() fails")

    monkeypatch.setattr(app, "create_audio_provider", lambda _config: provider)
    monkeypatch.setattr(
        app, "WebSocketStateServer", lambda _host, _port: websocket_server
    )
    monkeypatch.setattr(app, "StaticServer", FailingStaticServer)

    async def runner() -> None:
        await app.run(AppConfig(provider="fake"))

    with pytest.raises(RuntimeError, match="bind failed"):
        asyncio.run(runner())

    assert provider.started is True
    assert provider.stopped is True
    assert websocket_server.started is True
    assert websocket_server.stopped is True


def test_windows_audio_session_provider_requires_start() -> None:
    from vpook.audio.windows_audio_session_provider import WindowsAudioSessionProvider

    provider = WindowsAudioSessionProvider(process_name="discord")

    with pytest.raises(RuntimeError, match="Provider not started"):
        provider.read_level()


def test_windows_audio_session_provider_clears_smoothed_state_on_restart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from vpook.audio.windows_audio_session_provider import WindowsAudioSessionProvider

    refresh_calls = 0

    def fake_refresh(self: object) -> None:
        nonlocal refresh_calls
        refresh_calls += 1
        self._last_refresh = time.monotonic()
        self._meters = [SimpleNamespace(GetPeakValue=lambda: 0.8)]

    monkeypatch.setattr(WindowsAudioSessionProvider, "_refresh_sessions", fake_refresh)

    provider = WindowsAudioSessionProvider(process_name="discord")
    provider.start()
    first = provider.read_level()
    provider.stop()
    provider.start()
    second = provider.read_level()

    assert refresh_calls == 2
    assert first.volume == pytest.approx(0.8)
    assert second.volume == pytest.approx(0.8)


def test_windows_wasapi_start_cleans_up_pyaudio_when_device_lookup_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_module = _import_windows_wasapi_provider(monkeypatch)

    terminated: list[bool] = []

    class FakePyAudio:
        def terminate(self) -> None:
            terminated.append(True)

    fake_pyaudio_module = sys.modules["pyaudiowpatch"]
    monkeypatch.setattr(fake_pyaudio_module, "PyAudio", FakePyAudio)
    monkeypatch.setattr(
        provider_module.WindowsWasapiProvider,
        "_find_loopback_device",
        lambda self: (_ for _ in ()).throw(RuntimeError("no device")),
    )

    provider = provider_module.WindowsWasapiProvider()
    with pytest.raises(RuntimeError, match="no device"):
        provider.start()

    assert terminated == [True]
    assert provider._pa is None
    assert provider._stream is None


def test_windows_wasapi_empty_buffer_reads_as_silence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_module = _import_windows_wasapi_provider(monkeypatch)
    provider = provider_module.WindowsWasapiProvider()
    provider._stream = SimpleNamespace(read=lambda *args, **kwargs: b"")

    level = provider.read_level()

    assert level.volume == 0.0
    assert math.isfinite(level.timestamp)


def _import_windows_wasapi_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> ModuleType:
    fake_numpy = ModuleType("numpy")
    fake_numpy.float32 = float
    fake_numpy.int16 = "int16"
    fake_numpy.frombuffer = lambda raw, dtype=None: _FakeArray(raw)
    fake_numpy.sqrt = math.sqrt
    fake_numpy.mean = lambda values: sum(values) / len(values)

    fake_pyaudio = ModuleType("pyaudiowpatch")
    fake_pyaudio.PyAudio = object
    fake_pyaudio.Stream = object
    fake_pyaudio.paInt16 = 8
    fake_pyaudio.paWASAPI = 13

    monkeypatch.setitem(sys.modules, "numpy", fake_numpy)
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", fake_pyaudio)
    sys.modules.pop("vpook.audio.windows_wasapi_provider", None)
    return importlib.import_module("vpook.audio.windows_wasapi_provider")


class _FakeArray(list[float]):
    def __init__(self, raw: bytes) -> None:
        values = []
        for index in range(0, len(raw), 2):
            chunk = raw[index : index + 2]
            if len(chunk) == 2:
                values.append(float(int.from_bytes(chunk, "little", signed=True)))
        super().__init__(values)

    def astype(self, _dtype: object) -> _FakeArray:
        return self

    @property
    def size(self) -> int:
        return len(self)

    def __pow__(self, power: int) -> list[float]:
        return [value**power for value in self]
