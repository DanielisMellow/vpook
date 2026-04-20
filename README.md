# vpook

`vpook` is a local avatar overlay service for OBS-style scenes. It serves a small browser overlay over HTTP, publishes live talking state over WebSocket, and swaps between idle and talking avatar images based on detected audio activity.

## What It Does

- Serves the overlay UI at `http://127.0.0.1:8000`
- Broadcasts live voice state at `ws://127.0.0.1:8765`
- Detects voice activity with configurable threshold, attack, and release timing
- Supports three audio backends (fake, full-device loopback, per-app session metering)
- Serves avatar assets from `apps/assets`

## Repository Layout

- `apps/overlay_service.py`: entrypoint — parses args and starts the service
- `apps/overlay_service_args.py`: argument parsing and config building
- `apps/overlay_service_logging.py`: logging setup
- `apps/assets/`: user-owned avatar images served by the HTTP server
- `src/vpook/app.py`: main application loop
- `src/vpook/config.py`: runtime configuration defaults
- `src/vpook/audio/`: audio provider implementations
- `src/vpook/state/voice_state.py`: threshold, attack, and release logic
- `src/vpook/transport/`: HTTP and WebSocket servers
- `src/vpook/overlay/`: browser overlay files

## Requirements

- Windows (for live audio capture via WASAPI)
- Python 3.12
- [`just`](https://github.com/casey/just) task runner
- OBS or any browser source consumer to display the overlay visually

## Setup

### Windows PowerShell

**1. Install Python 3.12**

```powershell
winget install Python.Python.3.12
```

Close and reopen PowerShell after this so `python` is on your PATH.

**2. Install `just`**

```powershell
winget install Casey.Just
```

**3. Clone the repo and create a virtual environment**

```powershell
git clone <repo-url>
cd vpook
python -m venv .venv
```

**4. Activate the virtual environment**

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run this once and then retry step 4:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**5. Install vpook**

```powershell
just install-windows
```

You should see `(.venv)` in your prompt before running any `just` commands. Re-run step 4 any time you open a new terminal.

### macOS or Linux

The fake provider works cross-platform for development.

```bash
python3 -m venv .venv
source .venv/bin/activate
just install
```

## Running The Service

From the repo root with the virtual environment active:

```bash
just run               # fake audio (default, cross-platform)
just run-discord       # per-app session metering targeting Discord
just run-lan           # bind to all interfaces for LAN access (WASAPI)
```

Extra flags are passed through to the entrypoint:

```bash
just run --wasapi
just run --process --target-process chrome
```

Once the service is running:

- Open `http://127.0.0.1:8000` in a browser to preview the overlay
- Add that URL as a Browser Source in OBS if you want to use it in a scene

### LAN / Local Network

`just run-lan` binds both servers to `0.0.0.0` so other devices on your network can use the overlay. The service auto-detects your LAN IP and uses it in `config.json` so remote browsers connect to the right WebSocket address.

On another device (or OBS on a separate PC):

1. Add `http://<your-ip>:8000` as a Browser Source
2. Both ports `8000` (HTTP) and `8765` (WebSocket) must be reachable — Windows Defender will prompt to allow them on first run

To use a specific Discord audio session over LAN:

```bash
just run --host 0.0.0.0 --process --target-process discord
```

## Selecting An Audio Provider

The CLI entrypoint (`overlay_service_args.py`) accepts flags to choose a provider. Pass exactly one provider flag.

### Fake (default — cross-platform)

```bash
just run
# or explicitly:
just run --fake
```

Generates a deterministic idle/talking cycle. No audio hardware required. Good for verifying the overlay and WebSocket transport without needing Windows.

### Device loopback — capture everything on an output device

```bash
just run --wasapi
# target a specific device by name substring:
just run --wasapi --audio-device "Headphones"
```

Captures the full mix of whatever is playing through a Windows output device via WASAPI loopback. Picks up all apps at once — Discord, game audio, music, everything.

### Per-app session metering — isolate one application

```bash
just run --process --target-process discord
# shortcut:
just run-discord
```

Uses the Windows Audio Session API (`IAudioMeterInformation`) to read the peak volume for a specific process only. Discord is the default target. Useful when streaming — game audio won't bleed into voice detection. The service auto-recovers if the target app is restarted.

### All available flags

```
--fake                      Use fake sine-wave audio (default)
--wasapi                    Capture system audio via WASAPI loopback
--process                   Capture a specific app's audio via Windows Audio Session API
--target-process NAME       Process name substring to monitor (default: discord)
--audio-device NAME         Loopback device name substring (default: system output)
--threshold FLOAT           Volume threshold for VAD (default: 0.08)
--attack-ms MS              Time above threshold before switching to talking (default: 120)
--release-ms MS             Time below threshold before switching to idle (default: 300)
--host HOST                 Bind address for both HTTP and WebSocket (overrides --http-host and --websocket-host)
--http-host HOST            HTTP bind address (default: 127.0.0.1)
--http-port PORT            HTTP port (default: 8000)
--websocket-host HOST       WebSocket bind address (default: 127.0.0.1)
--websocket-port PORT       WebSocket port (default: 8765)
--tick-ms MS                Main loop interval (default: 50)
--log-level LEVEL           DEBUG, INFO, WARNING, or ERROR (default: INFO)
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

## Architecture

### High-Level Flow

1. `apps/overlay_service.py` parses CLI flags, builds an `AppConfig`, and starts the app.
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

`src/vpook/audio/windows_audio_session_provider.py`

- Uses `IAudioMeterInformation` (Windows Audio Session API via `pycaw`) to meter a specific process's audio output.
- Tracks all audio sessions matching the target process name and takes the peak across them.
- Re-enumerates sessions every 5 seconds so the provider recovers automatically if the app restarts.

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

Pass flags when running:

```bash
just run --threshold 0.05 --attack-ms 80 --release-ms 500
```

Or edit defaults in `src/vpook/config.py`:

- `threshold`
- `attack_ms`
- `release_ms`

### Change Bind Addresses Or Ports

```bash
just run --http-port 8080 --websocket-port 9000
```

Or edit these in `AppConfig`:

- `http_host`
- `http_port`
- `websocket_host`
- `websocket_port`

## Troubleshooting

### `ModuleNotFoundError: No module named 'vpook'`

`vpook` uses a `src/` layout, so the package must be installed into the active environment first. From the repo root, run:

```bash
just install
```

On Windows, use:

```powershell
just install-windows
```

Then rerun the service.

### WebSocket Or HTTP Bind Errors

If you see an address-in-use or bind failure:

- check whether another process is already using port `8000` or `8765`
- pass different ports: `just run --http-port 8080 --websocket-port 9000`

### No Real Audio On Windows

**Device loopback (`--wasapi`):**
- confirm `.[windows-audio]` was installed (`just install-windows`)
- confirm the selected output device is active and playing audio
- pass `--audio-device` with a substring of the target device name if the default isn't picked up

**Per-app session metering (`--process`):**
- confirm `.[windows-audio]` was installed (`just install-windows`)
- make sure the target app is open and joined to a voice channel — Windows only creates an audio session once the app is actively outputting audio
- if the app was just launched, wait up to 5 seconds for the session to be discovered
- check logs for `No active audio sessions found for process '...'`

### Overlay Loads But Never Animates

- open browser devtools and confirm `/config.json` loads
- confirm the WebSocket connection to `ws://127.0.0.1:8765` succeeds
- verify the backend logs show voice state transitions
- if using real audio, lower the threshold: `just run --threshold 0.04`

## Development

Formatting and linting are wired through `ruff`:

```bash
just lint
just lint-verbose
just format
just format-diff
```
