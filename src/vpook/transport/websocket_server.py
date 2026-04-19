"""WebSocket server that broadcasts overlay state to connected clients."""

from __future__ import annotations

import asyncio
import json
import logging

import websockets
from websockets.server import WebSocketServerProtocol

from vpook.models import OverlayState


class WebSocketStateServer:
    """Manage WebSocket connections and broadcast overlay state."""

    def __init__(self, host: str, port: int) -> None:
        """Initialize the server.

        Args:
            host: Interface to bind for incoming WebSocket clients.
            port: TCP port to bind for incoming WebSocket clients.
        """
        self._logger = logging.getLogger(__name__)
        self.host = host
        self.port = port
        self._clients: set[WebSocketServerProtocol] = set()
        self._listener = None
        self._latest_state: OverlayState | None = None
        self._last_talking: bool | None = None
        self._logger.debug(
            "Initialized WebSocket state server for ws://%s:%s.", host, port
        )

    async def start(self) -> None:
        """Start listening for WebSocket connections."""
        self._listener = await websockets.serve(
            self._handle_client, self.host, self.port
        )
        self._logger.info(
            "WebSocket state server running at ws://%s:%s.", self.host, self.port
        )

    async def stop(self) -> None:
        """Close all client connections and shut down the server."""
        if self._listener is None:
            return

        self._logger.info(
            "Stopping WebSocket state server with %s connected client(s).",
            len(self._clients),
        )
        for client in list(self._clients):
            await client.close()

        self._listener.close()
        await self._listener.wait_closed()
        self._listener = None
        self._logger.debug("WebSocket state server stopped.")

    async def broadcast(self, state: OverlayState) -> None:
        """Send the current overlay state to all connected clients.

        Args:
            state: Overlay state snapshot to broadcast.
        """
        self._latest_state = state
        if state.talking != self._last_talking:
            self._last_talking = state.talking
            self._logger.info(
                "Broadcasting voice state change: talking=%s volume=%.3f clients=%s.",
                state.talking,
                state.volume,
                len(self._clients),
            )
        if not self._clients:
            return

        message = json.dumps(state.to_payload())
        clients = list(self._clients)
        results = await asyncio.gather(
            *(client.send(message) for client in clients),
            return_exceptions=True,
        )
        for client, result in zip(clients, results, strict=False):
            if isinstance(result, Exception):
                self._logger.warning(
                    "Dropping WebSocket client after send failure: %s", result
                )
                self._clients.discard(client)

    async def _handle_client(self, websocket: WebSocketServerProtocol) -> None:
        self._clients.add(websocket)
        self._logger.info("WebSocket client connected. clients=%s", len(self._clients))
        try:
            if self._latest_state is not None:
                await websocket.send(json.dumps(self._latest_state.to_payload()))
                self._logger.debug(
                    "Sent latest state snapshot to new WebSocket client."
                )
            async for _ in websocket:
                continue
        finally:
            self._clients.discard(websocket)
            self._logger.info(
                "WebSocket client disconnected. clients=%s", len(self._clients)
            )
