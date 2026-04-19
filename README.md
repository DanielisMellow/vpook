# vpook

`vpook` is a local avatar overlay service for OBS-style scenes. It serves a small browser overlay over HTTP, publishes live talking state over WebSocket, and swaps between idle and talking avatar images based on detected audio activity.

## What It Does

- Serves the overlay UI at `http://127.0.0.1:8000`
- Broadcasts live voice state at `ws://127.0.0.1:8765`
- Supports a fake audio provider for development
- Supports Windows WASAPI loopback for real system-audio capture
- Serves avatar assets from `apps/assets`

## Repository Layout

- `apps/overlay_service.py`: configurable entrypoint for running the service
- `apps/overlay_service_logging.py`: logging setup
- `apps/assets/`: user-owned avatar images served by the HTTP server
- `src/vpook/app.py`: main application loop
- `src/vpook/config.py`: runtime configuration defaults
- `src/vpook/audio/`: audio provider implementations
- `src/vpook/state/voice_state.py`: threshold, attack, and release logic
- `src/vpook/transport/`: HTTP and WebSocket servers
- `src/vpook/overlay/`: browser overlay files

## Requirements

- Python `3.12+`
- Windows if you want live WASAPI loopback audio
- OBS or any browser source consumer if you want to use the overlay visually

## Setup

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .[windows-audio]
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

### macOS or Linux

The fake provider works cross-platform for development.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

## Running The Service

From the repo root:

```bash
python apps/overlay_service.py
```

The entrypoint now bootstraps `src/` automatically, so you do not need to set `PYTHONPATH`.

Once the service is running:

- Open `http://127.0.0.1:8000` in a browser to preview the overlay
- Add that URL as a Browser Source in OBS if you want to use it in a scene

## Switching Between Fake And Real Audio

The main runtime toggle lives in `apps/overlay_service.py`.

By default:

- `USE_FAKE_AUDIO = True`
- The service uses a deterministic fake signal so the avatar visibly animates

For real Windows audio capture:

- Set `USE_FAKE_AUDIO = False`
- Optionally set `WINDOWS_LOOPBACK_DEVICE_NAME` to part of a speaker or headset name
- If `WINDOWS_LOOPBACK_DEVICE_NAME` is `None`, the app tries to mirror the default Windows output device

Example:

```python
USE_FAKE_AUDIO = False
WINDOWS_LOOPBACK_DEVICE_NAME = "Headphones"
```

## Assets

Default avatar image paths are defined in `src/vpook/config.py`:

- Idle image: `/assets/pookie/idle.png`
- Talking image: `/assets/pookie/talking.png`

Those HTTP paths resolve to files under:

```text
apps/assets/
```

If you replace those files, the overlay will serve your new images. The HTTP server rejects asset paths that escape the asset root.

## Runtime Defaults

Current defaults from `AppConfig`:

- HTTP host: `127.0.0.1`
- HTTP port: `8000`
- WebSocket host: `127.0.0.1`
- WebSocket port: `8765`
- Tick interval: `50ms`
- Voice threshold: `0.08`
- Attack: `120ms`
- Release: `300ms`

## Architecture

### High-Level Flow

1. `apps/overlay_service.py` builds an `AppConfig` and starts the app.
2. `src/vpook/app.py` creates the audio provider, voice activity detector, WebSocket state server, and static HTTP server.
3. The app loop samples audio every `tick_ms`.
4. `VoiceActivityDetector` turns raw volume into a stable `talking` or `idle` state using threshold, attack, and release timing.
5. The current `OverlayState` is broadcast to connected browser clients over WebSocket.
6. The browser overlay swaps images and applies transforms based on the state payload.

### Backend Components

`src/vpook/audio/base.py`

- Defines the provider interface used by the app loop.

`src/vpook/audio/fake_provider.py`

- Generates a deterministic idle/talking cycle for local development.
- Useful when you want to verify animation and transport behavior without real audio input.

`src/vpook/audio/windows_wasapi_provider.py`

- Captures Windows system output audio through WASAPI loopback.
- Computes RMS volume from audio buffers.
- Applies a small smoothing window to reduce visual strobing.

`src/vpook/state/voice_state.py`

- Implements threshold-based state transitions.
- `attack_ms` avoids flipping to talking on tiny spikes.
- `release_ms` avoids flickering back to idle too aggressively.

`src/vpook/transport/websocket_server.py`

- Accepts browser clients over WebSocket.
- Stores the latest overlay state.
- Broadcasts JSON messages of type `state`.

`src/vpook/transport/static_server.py`

- Serves `index.html`, `app.js`, `styles.css`, and `config.json`.
- Also serves avatar assets from `apps/assets`.
- Builds `config.json` dynamically so the frontend knows which WebSocket URL and image paths to use.

### Frontend Overlay

`src/vpook/overlay/index.html`

- Minimal document with a single avatar image element.

`src/vpook/overlay/app.js`

- Fetches `/config.json`
- Connects to the WebSocket server
- Applies avatar image swaps and transform effects based on incoming state

The browser client does not do voice detection itself. It only renders the state computed by the Python service.

## Common Changes

### Change The Avatar

- Replace files in `apps/assets/pookie/`
- Or update the avatar paths in `AppConfig`

### Tune Detection Sensitivity

Edit values in `src/vpook/config.py`:

- `threshold`
- `attack_ms`
- `release_ms`

### Change Bind Addresses Or Ports

Edit these in `AppConfig`:

- `http_host`
- `http_port`
- `websocket_host`
- `websocket_port`

## Troubleshooting

### `ModuleNotFoundError: No module named 'vpook'`

This was fixed in `apps/overlay_service.py` by adding the repo `src/` directory to `sys.path`. Running from the repo root with:

```bash
python apps/overlay_service.py
```

should be the expected path.

### WebSocket Or HTTP Bind Errors

If you see an address-in-use or bind failure:

- check whether another process is already using port `8000` or `8765`
- change the ports in `AppConfig`
- rerun the service

### No Real Audio On Windows

- make sure you installed `.[windows-audio]`
- set `USE_FAKE_AUDIO = False`
- confirm the selected output device is active
- if needed, set `WINDOWS_LOOPBACK_DEVICE_NAME` to a substring of the target device name

### Overlay Loads But Never Animates

- open browser devtools and confirm `/config.json` loads
- confirm the WebSocket connection to `ws://127.0.0.1:8765` succeeds
- verify the backend logs show voice state transitions
- if using real audio, lower the threshold slightly

## Development

Formatting and linting are wired through `ruff`:

```bash
make lint
make format
```
