"""SensorStream: all buffered channels of one topic, plus rate statistics."""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Iterable, Optional, Tuple

import numpy as np

from .buffers import RingBuffer
from .stats import RateEstimator

Snapshot = Dict[str, Tuple[np.ndarray, np.ndarray]]


class SensorStream:
    """Holds one RingBuffer per channel of a single topic.

    ``spec`` is a ``sensorscope.sensors.base.SensorSpec`` (duck-typed here so
    this module stays free of any dependency on it).
    """

    def __init__(self, topic: str, spec: Any, capacity: int = 20000) -> None:
        self.topic = topic
        self.spec = spec
        self.capacity = capacity
        self.buffers: Dict[str, RingBuffer] = {c: RingBuffer(capacity) for c in spec.channels}
        self.rate = RateEstimator()
        self.extra: Any = None  # latest non-scalar payload (e.g. scan points)
        self._lock = threading.Lock()
        self._last_t = float("-inf")
        self._last_wall: Optional[float] = None

    def push(self, t: float, channels: Dict[str, float], extra: Any = None) -> None:
        with self._lock:
            if t < self._last_t:  # clock jumped back (sim reset / bag loop)
                self._clear_locked()
            for name, buf in self.buffers.items():
                buf.append(t, float(channels.get(name, float("nan"))))
            self.rate.tick(t)
            self.extra = extra
            self._last_t = t
            self._last_wall = time.monotonic()

    def _clear_locked(self) -> None:
        for buf in self.buffers.values():
            buf.clear()
        self.rate.reset()
        self.extra = None
        self._last_t = float("-inf")

    def clear(self) -> None:
        with self._lock:
            self._clear_locked()

    def seconds_since_last(self) -> Optional[float]:
        """Wall-clock seconds since the last message, or None if none yet."""
        if self._last_wall is None:
            return None
        return time.monotonic() - self._last_wall

    def snapshot(self, window_s: Optional[float] = None,
                 channels: Optional[Iterable[str]] = None) -> Snapshot:
        """Consistent copy of the requested channels (all channels aligned)."""
        names = list(channels) if channels is not None else list(self.buffers)
        with self._lock:
            return {n: self.buffers[n].get(window_s) for n in names}

    def to_csv(self, path: str, window_s: Optional[float] = None) -> int:
        """Write the buffered data to CSV. Returns the number of rows."""
        snap = self.snapshot(window_s)
        names = list(snap)
        t = snap[names[0]][0]
        data = np.column_stack([t] + [snap[n][1] for n in names])
        np.savetxt(path, data, delimiter=",", header=",".join(["time_s"] + names),
                   comments="")
        return int(t.size)
