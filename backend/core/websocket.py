"""
WebSocket connection manager for real-time job progress updates.

Each job may have multiple browser tabs connected; all receive the same
broadcast.  Connections are keyed by ``job_id`` so messages are scoped
to the relevant generation run.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages the lifecycle of WebSocket connections grouped by job id."""

    def __init__(self) -> None:
        # job_id → list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = defaultdict(list)

    # ------------------------------------------------------------------ #
    # Connection lifecycle
    # ------------------------------------------------------------------ #
    async def connect(self, websocket: WebSocket, job_id: str) -> None:
        """Accept *websocket* and register it under *job_id*."""
        await websocket.accept()
        self.active_connections[job_id].append(websocket)
        logger.debug("WS connected: job_id=%s total=%d", job_id, len(self.active_connections[job_id]))

    def disconnect(self, websocket: WebSocket, job_id: str) -> None:
        """Remove *websocket* from the pool for *job_id*.

        Cleans up the key entirely when the last connection is removed so
        that the dict does not grow unboundedly.
        """
        connections = self.active_connections.get(job_id, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            self.active_connections.pop(job_id, None)
        logger.debug("WS disconnected: job_id=%s remaining=%d", job_id, len(connections))

    # ------------------------------------------------------------------ #
    # Messaging helpers
    # ------------------------------------------------------------------ #
    async def send_personal_message(self, websocket: WebSocket, data: dict) -> None:
        """Send *data* as JSON to a single *websocket*."""
        try:
            await websocket.send_text(json.dumps(data))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to send personal WS message: %s", exc)

    async def send_job_update(self, job_id: str, data: dict) -> None:
        """Broadcast *data* to **all** WebSocket connections for *job_id*.

        Dead connections are silently removed from the pool.
        """
        connections = list(self.active_connections.get(job_id, []))
        if not connections:
            return

        payload = json.dumps(data)
        dead: list[WebSocket] = []

        for ws in connections:
            try:
                await ws.send_text(payload)
            except Exception as exc:  # noqa: BLE001
                logger.warning("WS send failed (job=%s): %s — removing connection", job_id, exc)
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws, job_id)

    async def broadcast(self, data: dict) -> None:
        """Send *data* to **every** connected WebSocket across all jobs.

        Intended for system-wide notifications (e.g. server shutdown warning).
        """
        payload = json.dumps(data)
        dead: list[tuple[str, WebSocket]] = []

        for job_id, connections in list(self.active_connections.items()):
            for ws in list(connections):
                try:
                    await ws.send_text(payload)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("WS broadcast failed (job=%s): %s", job_id, exc)
                    dead.append((job_id, ws))

        for job_id, ws in dead:
            self.disconnect(ws, job_id)

    # ------------------------------------------------------------------ #
    # Introspection
    # ------------------------------------------------------------------ #
    def connection_count(self, job_id: str | None = None) -> int:
        """Return the number of active connections, optionally filtered by job."""
        if job_id is not None:
            return len(self.active_connections.get(job_id, []))
        return sum(len(conns) for conns in self.active_connections.values())


# Singleton instance shared across the application
manager = ConnectionManager()
