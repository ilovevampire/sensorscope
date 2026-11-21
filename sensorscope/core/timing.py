# Copyright 2026 Vishal Gaud
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Message timing analysis: rate, jitter, latency and dropped-sample estimates.

Two clocks are compared when header stamps exist:
  * receive time  (when SensorScope got the message), and
  * header stamp  (when the driver says the measurement was taken).
Jitter of the stamps is the sensor/driver's own regularity; jitter of the
receive times additionally includes DDS and executor scheduling delay.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import threading
from typing import Optional

import numpy as np

NAN = float('nan')


@dataclass
class TimingStats:
    n: int = 0
    has_stamps: bool = False
    rate_hz: float = NAN  # from stamps if available, else receive time
    recv_jitter_ms: float = NAN  # std of receive-time intervals
    stamp_jitter_ms: float = NAN  # std of header-stamp intervals
    latency_mean_ms: float = NAN  # receive - stamp (needs synced clocks)
    latency_std_ms: float = NAN
    latency_max_ms: float = NAN
    dropped_est: int = 0  # missing messages inferred from large gaps
    out_of_order: int = 0  # negative time steps


def analyze_timing(t, stamp: Optional[np.ndarray] = None) -> TimingStats:
    t = np.asarray(t, dtype=float)
    n = int(t.size)
    if n < 3:
        return TimingStats(n=n)
    dt = np.diff(t)
    out = TimingStats(n=n, recv_jitter_ms=float(np.std(dt) * 1e3))

    ref = dt
    span = t[-1] - t[0]
    if stamp is not None:
        s = np.asarray(stamp, dtype=float)
        ok = np.isfinite(s) & (s > 0)
        if ok.sum() >= 3 and ok.mean() > 0.9:
            s, tt = s[ok], t[ok]
            ds = np.diff(s)
            lat = (tt - s) * 1e3
            out.has_stamps = True
            out.stamp_jitter_ms = float(np.std(ds) * 1e3)
            out.latency_mean_ms = float(np.mean(lat))
            out.latency_std_ms = float(np.std(lat))
            out.latency_max_ms = float(np.max(lat))
            ref, span = ds, s[-1] - s[0]

    out.out_of_order = int(np.sum(ref < 0))
    pos = ref[ref > 0]
    if pos.size:
        med = float(np.median(pos))
        out.dropped_est = int(np.sum(np.maximum(np.round(ref / med) - 1.0, 0.0)))
    out.rate_hz = float((ref.size) / span) if span > 0 else NAN
    return out


class TimingTracker:
    """Rolling window of (receive, stamp) pairs for the live header."""

    def __init__(self, window: int = 500) -> None:
        self._recv: deque = deque(maxlen=window)
        self._stamp: deque = deque(maxlen=window)
        self._lock = threading.Lock()

    def tick(self, t_recv: float, t_stamp: Optional[float]) -> None:
        with self._lock:
            self._recv.append(t_recv)
            self._stamp.append(NAN if t_stamp is None else t_stamp)

    def reset(self) -> None:
        with self._lock:
            self._recv.clear()
            self._stamp.clear()

    def stats(self) -> TimingStats:
        with self._lock:
            t = np.array(self._recv, dtype=float)
            s = np.array(self._stamp, dtype=float)
        return analyze_timing(t, s)
