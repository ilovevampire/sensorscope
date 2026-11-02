"""Rate/jitter estimation and summary statistics."""

from __future__ import annotations

import threading
from collections import deque
from typing import Dict, Iterable

import numpy as np

STAT_KEYS = ("last", "mean", "std", "min", "max", "rms")


class RateEstimator:
    """Estimates message rate (Hz) and inter-arrival jitter (ms)."""

    def __init__(self, window: int = 200) -> None:
        self._times: deque = deque(maxlen=window)
        self._lock = threading.Lock()
        self.count = 0

    def tick(self, t: float) -> None:
        with self._lock:
            self._times.append(t)
            self.count += 1

    def reset(self) -> None:
        with self._lock:
            self._times.clear()
            self.count = 0

    def _times_array(self) -> np.ndarray:
        with self._lock:
            return np.array(self._times, dtype=float)

    @property
    def rate_hz(self) -> float:
        times = self._times_array()
        if times.size < 2:
            return 0.0
        span = times[-1] - times[0]
        return float((times.size - 1) / span) if span > 0 else 0.0

    @property
    def jitter_ms(self) -> float:
        """Standard deviation of the inter-arrival time, in milliseconds."""
        dts = np.diff(self._times_array())
        return float(np.std(dts) * 1000.0) if dts.size >= 2 else 0.0


def summarize(values: Iterable[float]) -> Dict[str, float]:
    """Summary statistics over the finite values (NaN/inf are ignored)."""
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {k: float("nan") for k in STAT_KEYS}
    return {
        "last": float(v[-1]),
        "mean": float(v.mean()),
        "std": float(v.std()),
        "min": float(v.min()),
        "max": float(v.max()),
        "rms": float(np.sqrt(np.mean(v**2))),
    }
