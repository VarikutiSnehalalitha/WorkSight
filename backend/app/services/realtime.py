"""Role-Filtered WebSocket Connection Manager for Real-Time Dashboard & Alerts."""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket


@dataclass
class ConnectedClient:
    websocket: WebSocket
    user_id: int
    role: str
    managed_department_id: Optional[int] = None


class RealtimeHub:
    def __init__(self) -> None:
        self._clients: List[ConnectedClient] = []
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
        role: str,
        managed_department_id: Optional[int] = None,
    ) -> ConnectedClient:
        await websocket.accept()
        client = ConnectedClient(
            websocket=websocket,
            user_id=user_id,
            role=role,
            managed_department_id=managed_department_id,
        )
        async with self._lock:
            self._clients.append(client)
        return client

    async def disconnect(self, client: ConnectedClient) -> None:
        async with self._lock:
            if client in self._clients:
                self._clients.remove(client)

    async def broadcast(
        self,
        event_type: str,
        payload: Dict[str, Any],
        allowed_roles: Optional[Set[str]] = None,
        target_user_id: Optional[int] = None,
        department_id: Optional[int] = None,
    ) -> None:
        message = json.dumps({"type": event_type, "payload": payload})
        stale: List[ConnectedClient] = []

        async with self._lock:
            clients_snapshot = list(self._clients)

        for client in clients_snapshot:
            if target_user_id is not None and client.user_id != target_user_id:
                continue
            if allowed_roles is not None and client.role not in allowed_roles:
                continue
            if (
                department_id is not None
                and client.role == "dept_manager"
                and client.managed_department_id != department_id
            ):
                continue
            try:
                await client.websocket.send_text(message)
            except Exception:
                stale.append(client)

        if stale:
            async with self._lock:
                for client in stale:
                    if client in self._clients:
                        self._clients.remove(client)


realtime_hub = RealtimeHub()
