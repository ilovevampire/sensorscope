"""Fixed-size, thread-safe circular buffer for (time, value) samples."""

from __future__ import annotations

import threading
from typing import Optional, Tuple

import numpy as np


class RingBuffer:
    """Circular buffer holding the most recent ``capacity`` samples.

    Written from the ROS thread, read from the GUI thread, so every access
    goes through a lock. ``get`` always returns copies ordered oldest-first.
    """

    def __init__(self, capacity: int = 20000) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = int(capacity)
        self._t = np.zeros(self.capacity, dtype=float)
        self._v = np.zeros(self.capacity, dtype=float)
        self._head = 0  # index of the next write
        self._count = 0
        self._lock = threading.Lock()

    def append(self, t: float, v: float) -> None:
        with self._lock:
            self._t[self._head] = t
            self._v[self._head] = v
            self._head = (self._head + 1) % self.capacity
            if self._count < self.capacity:
                self._count += 1

    def __len__(self) -> int:
        return self._count

    def clear(self) -> None:
        with self._lock:
            self._head = 0
            self._count = 0

    def get(self, window_s: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
        """Return ``(t, v)`` copies, oldest first.

        If ``window_s`` is given, only samples within the last ``window_s``
        seconds (relative to the newest sample) are returned.
        """
        with self._lock:
            n = self._count
            if n == 0:
                return np.empty(0), np.empty(0)
            oldest = (self._head - n) % self.capacity
            idx = (oldest + np.arange(n)) % self.capacity
            t = self._t[idx]
            v = self._v[idx]
        if window_s is not None:
            start = int(np.searchsorted(t, t[-1] - window_s, side="left"))
            t, v = t[start:], v[start:]
        return t, v
