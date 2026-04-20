"""Threaded HTTP server that serves the OBS overlay static files."""

from __future__ import annotations

import json
import logging
import mimetypes
import socket
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from vpook.config import AppConfig


def _resolve_websocket_host(host: str) -> str:
    """Resolve bind address to a routable address for use in config.json.

    When the server binds to ``0.0.0.0``, remote clients cannot use that as a
    WebSocket address. This function detects the machine's LAN IP in that case
    so the browser receives a URL it can actually connect to.
    """
    if host == "0.0.0.0":
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return host
    return host


class StaticServer:
    """Serve overlay HTML, static assets, and generated config over HTTP."""

    def __init__(self, config: AppConfig) -> None:
        """Initialize the server.

        Args:
            config: Application configuration describing bind address and
                asset locations.
        """
        self._logger = logging.getLogger(__name__)
        self.config = config
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._overlay_dir = Path(__file__).resolve().parent.parent / "overlay"
        self._logger.debug(
            "Initialized static server for http://%s:%s with assets_dir=%s.",
            config.http_host,
            config.http_port,
            config.assets_dir,
        )

    def start(self) -> None:
        """Build the request handler and start the HTTP server."""
        handler = self._build_handler()
        self._httpd = ThreadingHTTPServer(
            (self.config.http_host, self.config.http_port), handler
        )
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, name="vpook-http", daemon=True
        )
        self._thread.start()
        self._logger.info(
            "HTTP overlay server running at http://%s:%s.",
            self.config.http_host,
            self.config.http_port,
        )

    def stop(self) -> None:
        """Shut down the HTTP server and join the server thread."""
        if self._httpd is None:
            return
        self._logger.info("Stopping HTTP overlay server.")
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._httpd = None
        self._thread = None
        self._logger.debug("HTTP overlay server stopped.")

    def _build_handler(self) -> type[BaseHTTPRequestHandler]:
        config = self.config
        overlay_dir = self._overlay_dir
        assets_dir = config.assets_dir.resolve()

        class Handler(BaseHTTPRequestHandler):
            def __init__(self, *args: object, **kwargs: object) -> None:
                self._logger = logging.getLogger(__name__)
                super().__init__(*args, **kwargs)

            def do_GET(self) -> None:
                self._handle_request(include_body=True)

            def do_HEAD(self) -> None:
                self._handle_request(include_body=False)

            def _handle_request(self, include_body: bool) -> None:
                parsed = urlparse(self.path)
                route = parsed.path or "/"
                self._logger.debug("Handling %s request for %s.", self.command, route)
                if route in {"/", "/index.html"}:
                    self._serve_file(
                        overlay_dir / "index.html",
                        "text/html; charset=utf-8",
                        include_body,
                    )
                    return
                if route == "/app.js":
                    self._serve_file(
                        overlay_dir / "app.js",
                        "application/javascript; charset=utf-8",
                        include_body,
                    )
                    return
                if route == "/styles.css":
                    self._serve_file(
                        overlay_dir / "styles.css",
                        "text/css; charset=utf-8",
                        include_body,
                    )
                    return
                if route == "/config.json":
                    payload = {
                        "websocketUrl": f"ws://{_resolve_websocket_host(config.websocket_host)}:{config.websocket_port}",
                        "avatar": {
                            "idle": config.avatar.idle_image,
                            "talking": config.avatar.talking_image,
                            "talkingGlowColor": config.avatar.talking_glow_color,
                            "talkingGlowIntensity": config.avatar.talking_glow_intensity,
                        },
                    }
                    self._serve_bytes(
                        json.dumps(payload).encode("utf-8"),
                        "application/json; charset=utf-8",
                        include_body,
                    )
                    return
                if route.startswith("/assets/"):
                    relative_path = route.removeprefix("/assets/")
                    candidate = (assets_dir / unquote(relative_path)).resolve()
                    if assets_dir not in candidate.parents and candidate != assets_dir:
                        self._logger.warning(
                            "Rejected asset request outside asset root: %s", route
                        )
                        self.send_error(
                            HTTPStatus.FORBIDDEN, "Asset path escapes asset root."
                        )
                        return
                    if not candidate.is_file():
                        self._logger.warning("Asset not found for request: %s", route)
                        self.send_error(HTTPStatus.NOT_FOUND, "Asset not found.")
                        return
                    mime_type = (
                        mimetypes.guess_type(candidate.name)[0]
                        or "application/octet-stream"
                    )
                    self._serve_file(candidate, mime_type, include_body)
                    return

                self._logger.warning("Route not found: %s", route)
                self.send_error(HTTPStatus.NOT_FOUND, "Not found.")

            def log_message(self, format: str, *args: object) -> None:  # noqa: A002, ARG002
                return

            def _serve_file(
                self, path: Path, content_type: str, include_body: bool
            ) -> None:
                if not path.is_file():
                    self._logger.warning("Static file not found: %s", path)
                    self.send_error(HTTPStatus.NOT_FOUND, "File not found.")
                    return
                self._logger.debug("Serving file %s as %s.", path, content_type)
                self._serve_bytes(path.read_bytes(), content_type, include_body)

            def _serve_bytes(
                self, payload: bytes, content_type: str, include_body: bool
            ) -> None:
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                if include_body:
                    try:
                        self.wfile.write(payload)
                    except BrokenPipeError:
                        pass

        return Handler
