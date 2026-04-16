from __future__ import annotations

import json
import threading


class VenueUpdateHub:
    def __init__(self):
        self._clients = set()
        self._lock = threading.Lock()
        # POST handlers broadcast from worker threads while each WS has a recv thread; serialize sends.
        self._send_locks: dict[int, threading.Lock] = {}

    def add_client(self, ws) -> None:
        with self._lock:
            self._clients.add(ws)
            self._send_locks[id(ws)] = threading.Lock()

    def remove_client(self, ws) -> None:
        with self._lock:
            self._clients.discard(ws)
            self._send_locks.pop(id(ws), None)

    def broadcast(self, event: dict[str, object]) -> None:
        payload = json.dumps(event)
        with self._lock:
            clients = list(self._clients)
            locks = {id(ws): self._send_locks.get(id(ws)) for ws in clients}

        for ws in clients:
            send_lock = locks.get(id(ws))
            try:
                if send_lock is not None:
                    with send_lock:
                        ws.send(payload)
                else:
                    ws.send(payload)
            except Exception:
                self.remove_client(ws)
