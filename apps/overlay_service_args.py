"""Argument parsing for the overlay service."""

from __future__ import annotations

import argparse

from vpook.config import AppConfig


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
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
    )
