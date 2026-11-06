"""What a stranger with a script cannot do (the frontend audit, 2026-11-07 — reports/«Экраны защита и скорость фронтенда»).

The token is made by the phone (identity.py), so a script can make as many as it likes, and every new token is a new
person with a fresh day. Until App Attest proves a request comes from the real app on a real iPhone (stage 4), these
hold the doors that cost money or reach somebody's life:

  · BOB_PUBLIC=1 — a server anyone can reach. No request without a token: the anonymous bucket holds one real
    person's life from before tokens existed (identity.py), and without this anybody could read his diary or erase
    it with a bare `DELETE /api/me`. No developer pages. No word-for-word voice (/api/say verbatim), which would make
    his voice say anything for anyone, at our cost.
  · Every door that costs money is rate-limited per address (and making a companion, the dearest, per person too).
  · An uploaded utterance is at most MAX_AUDIO bytes: the ears bill by length, and a body read whole could be any size.

In-memory and per process: enough for one server. Behind a proxy, set TRUST_PROXY=1 so the address is the caller's,
not the proxy's (and only then — a client can write X-Forwarded-For itself).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, WebSocket

from . import config

#: per address (or per person, for "create-person"): how many requests, in how many seconds
LIMITS: dict[str, tuple[int, float]] = {
    "create": (4, 3600),          # a companion is written by several model calls: the dearest door
    "create-person": (6, 86400),
    "hello": (30, 3600),          # his first words cost a reply and a voice
    "talk": (240, 600),           # a turn every 2.5 s for ten minutes is far past any real talk
    "say": (60, 600),
    "intake": (120, 600),
    "live": (30, 600),            # opening the live channel
}


class Limiter:
    """A sliding window per key: at most n hits in the last `window` seconds."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, n: int, window: float) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window:
                hits.popleft()
            if len(hits) >= n:
                return False
            hits.append(now)
            if len(self._hits) > 50_000:                 # (a flood of addresses must not grow this forever)
                for k in [k for k, q in self._hits.items() if not q or now - q[-1] > 86400]:
                    del self._hits[k]
            return True

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


LIMITER = Limiter()


def address(client_host: str | None, forwarded: str | None) -> str:
    if config.TRUST_PROXY and forwarded:
        return forwarded.split(",")[0].strip()
    return client_host or "?"


def _refuse(window: float) -> HTTPException:
    return HTTPException(status_code=429, detail="Too many requests. Try again later.",
                         headers={"Retry-After": str(int(window))})


def limit(door: str):
    """A FastAPI dependency: this door, at most LIMITS[door] per address."""

    def check(request: Request) -> None:
        n, window = LIMITS[door]
        who = address(request.client.host if request.client else None, request.headers.get("x-forwarded-for"))
        if not LIMITER.allow(f"{door}:{who}", n, window):
            raise _refuse(window)

    return check


def limit_person(door: str, user_id: str) -> None:
    n, window = LIMITS[door]
    if not LIMITER.allow(f"{door}:{user_id}", n, window):
        raise _refuse(window)


def allow_socket(ws: WebSocket) -> bool:
    n, window = LIMITS["live"]
    who = address(ws.client.host if ws.client else None, ws.headers.get("x-forwarded-for"))
    return LIMITER.allow(f"live:{who}", n, window)
