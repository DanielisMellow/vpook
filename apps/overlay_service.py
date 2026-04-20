"""Entry point for the overlay service."""

from __future__ import annotations

from overlay_service_args import build_config, parse_args
from overlay_service_logging import configure_logging
from vpook.app import main

if __name__ == "__main__":
    args = parse_args()
    configure_logging(args.log_level)
    main(build_config(args))
