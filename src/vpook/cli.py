"""Console-script entry point for the overlay service.

Exposes ``main`` so the service can be launched as ``vpook`` once the
``[project.scripts]`` entry is installed (e.g. ``uv tool install`` or
``uv run vpook``). Mirrors the argument surface of
``apps/overlay_service_args.py``; keep the two in sync when adding flags.
"""

from __future__ import annotations

import argparse
import logging

from vpook.app import main as run_app
from vpook.config import AppConfig, AvatarConfig


def configure_logging(level_str: str = "INFO") -> None:
    """Configure application-wide logging behavior.

    Args:
        level_str: Logging level name (e.g., "DEBUG", "INFO", "WARNING", "ERROR").

    Raises:
        ValueError: If the level name is not a recognised logging level.
    """
    normalized_level = level_str.upper()
    level = getattr(logging, normalized_level, None)
    if not isinstance(level, int):
        raise ValueError(f"Unsupported log level: {level_str}")

    formatter = logging.Formatter("%(asctime)s [%(name)s] [%(levelname)s] %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(console_handler)
    root.setLevel(level)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the overlay service.

    Args:
        argv: Optional argument list; defaults to ``sys.argv`` when omitted.

    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        prog="vpook",
        description="vpook overlay service",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Audio provider selection
    provider_group = parser.add_mutually_exclusive_group()
    provider_group.add_argument(
        "--fake",
        dest="provider",
        action="store_const",
        const="fake",
        help="Use fake sine-wave audio (default).",
    )
    provider_group.add_argument(
        "--wasapi",
        dest="provider",
        action="store_const",
        const="windows-wasapi",
        help="Capture system audio via WASAPI loopback.",
    )
    provider_group.add_argument(
        "--process",
        dest="provider",
        action="store_const",
        const="windows-audio-session",
        help="Capture a specific application's audio via Windows Audio Session API.",
    )
    parser.set_defaults(provider="fake")

    # Provider-specific options
    parser.add_argument(
        "--target-process",
        default="discord",
        metavar="NAME",
        help="Process name substring to monitor (used with --process).",
    )
    parser.add_argument(
        "--audio-device",
        default=None,
        metavar="NAME",
        help="Loopback device name substring (used with --wasapi). Defaults to system output.",
    )

    # VAD tuning
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.08,
        metavar="FLOAT",
        help="Volume threshold for voice activity detection.",
    )
    parser.add_argument(
        "--attack-ms",
        type=int,
        default=120,
        metavar="MS",
        help="Time above threshold before switching to talking.",
    )
    parser.add_argument(
        "--release-ms",
        type=int,
        default=300,
        metavar="MS",
        help="Time below threshold before switching to idle.",
    )
    parser.add_argument(
        "--talking-glow-color",
        default="rgba(255, 15, 148, 0.91)",
        metavar="COLOR",
        help="CSS color for the talking glow, for example '#ff66cc' or 'rgba(255, 15, 148, 0.91)'.",
    )
    parser.add_argument(
        "--talking-glow-intensity",
        type=float,
        default=0.5,
        metavar="FLOAT",
        help="Multiplier for talking glow size and strength.",
    )

    # Transport
    parser.add_argument(
        "--host",
        default=None,
        metavar="HOST",
        help="Bind address for both HTTP and WebSocket servers. Overrides --http-host and --websocket-host.",
    )
    parser.add_argument("--http-host", default="127.0.0.1", metavar="HOST")
    parser.add_argument("--http-port", type=int, default=8000, metavar="PORT")
    parser.add_argument("--websocket-host", default="127.0.0.1", metavar="HOST")
    parser.add_argument("--websocket-port", type=int, default=8765, metavar="PORT")
    parser.add_argument(
        "--tick-ms",
        type=int,
        default=50,
        metavar="MS",
        help="Main loop interval in milliseconds.",
    )

    # Logging
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        metavar="LEVEL",
        help="Logging verbosity (DEBUG, INFO, WARNING, ERROR).",
    )

    return parser.parse_args(argv)


def build_config(args: argparse.Namespace) -> AppConfig:
    """Build an :class:`AppConfig` from parsed arguments.

    Args:
        args: Parsed command-line arguments.

    Returns:
        AppConfig: The runtime configuration for the service.
    """
    host = args.host
    return AppConfig(
        provider=args.provider,
        target_process=args.target_process,
        audio_device=args.audio_device,
        threshold=args.threshold,
        attack_ms=args.attack_ms,
        release_ms=args.release_ms,
        http_host=host if host is not None else args.http_host,
        http_port=args.http_port,
        websocket_host=host if host is not None else args.websocket_host,
        websocket_port=args.websocket_port,
        tick_ms=args.tick_ms,
        avatar=AvatarConfig(
            talking_glow_color=args.talking_glow_color,
            talking_glow_intensity=max(args.talking_glow_intensity, 0.0),
        ),
    )


def main(argv: list[str] | None = None) -> None:
    """Parse arguments, configure logging, and run the service.

    Args:
        argv: Optional argument list; defaults to ``sys.argv`` when omitted.
    """
    args = parse_args(argv)
    configure_logging(args.log_level)
    run_app(build_config(args))


if __name__ == "__main__":
    main()
