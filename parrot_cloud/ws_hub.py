from __future__ import annotations

import json
import threading


class VenueUpdateHub:
    def __init__(self):
        self._clients = set()
        self._lock = threading.Lock()

    def add_client(self, ws) -> None:
        with self._lock:
            self._clients.add(ws)

    def remove_client(self, ws) -> None:
        with self._lock:
            self._clients.discard(ws)

    def broadcast(self, event: dict[str, object]) -> None:
        payload = json.dumps(event)
        with self._lock:
            clients = list(self._clients)

        for ws in clients:
            try:
                ws.send(payload)
            except Exception:
                self.remove_client(ws)
