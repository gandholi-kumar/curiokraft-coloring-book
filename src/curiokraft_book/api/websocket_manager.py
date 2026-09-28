"""Resilient WebSocket Connection Manager for CurioKraft Publishing Studio.

Provides real-time event broadcasting to web clients for:
- Console log streaming into the <ConsoleLogDrawer />
- Live pipeline stage progress updates
- Multi-agent debate transcript events
- Immediate notification of page asset updates
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import WebSocket

logger = logging.getLogger("curiokraft.ws")


class ConnectionManager:
    """Manages active client WebSocket connections and event distribution."""

    def __init__(self, max_log_history: int = 300):
        self.active_connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._log_history: deque[dict[str, Any]] = deque(maxlen=max_log_history)

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register an incoming WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(
            f"WebSocket client connected. Active connections: {len(self.active_connections)}"
        )

        # Send initial handshake with recent log history
        await websocket.send_json(
            {
                "type": "handshake_ack",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "connected_clients": len(self.active_connections),
                "recent_logs": list(self._log_history),
            }
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a disconnected WebSocket."""
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(
            f"WebSocket client disconnected. Remaining connections: {len(self.active_connections)}"
        )

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a JSON message to all active WebSocket clients."""
        if not self.active_connections:
            return

        async with self._lock:
            connections = list(self.active_connections)

        dead_connections: list[WebSocket] = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.debug(f"Failed to send to client; marking dead: {e}")
                dead_connections.append(connection)

        if dead_connections:
            async with self._lock:
                for dead in dead_connections:
                    self.active_connections.discard(dead)

    async def broadcast_log(
        self,
        level: str,
        message: str,
        component: str = "pipeline",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Stream a structured log event to all connected clients and store in buffer."""
        log_event = {
            "id": str(uuid4()),
            "type": "log_event",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "component": component,
            "message": message,
            "context": context or {},
        }
        self._log_history.append(log_event)
        await self.broadcast(log_event)

    async def broadcast_progress(
        self,
        stage: str,
        progress_percentage: float,
        message: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Stream a stage progress update."""
        progress_event = {
            "type": "pipeline_progress",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "progress_percentage": round(progress_percentage, 2),
            "message": message,
            "details": details or {},
        }
        await self.broadcast(progress_event)

    async def broadcast_debate_turn(
        self,
        turn_index: int,
        speaker: str,
        proposal: str,
        verdict: str | None = None,
    ) -> None:
        """Stream a multi-agent debate event to the UI."""
        debate_event = {
            "type": "debate_turn",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "turn_index": turn_index,
            "speaker": speaker,
            "proposal": proposal,
            "verdict": verdict,
        }
        await self.broadcast(debate_event)

    def get_recent_logs(self) -> list[dict[str, Any]]:
        """Return snapshot of buffered logs."""
        return list(self._log_history)


# Global singleton instance
ws_manager = ConnectionManager()
