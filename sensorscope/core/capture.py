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

"""Long-running capture of one topic, for offline-style analysis (Allan variance etc.)."""

from __future__ import annotations

import array
from dataclasses import dataclass, field
import threading
from typing import Any, Dict, List, Optional

import numpy as np

NAN = float('nan')


@dataclass
class CaptureData:
    """An immutable-ish snapshot of a capture. Also produced by the rosbag reader."""

    topic: str
    spec: Any
    t: np.ndarray  # receive (or bag) time, seconds
    stamp: np.ndarray  # header stamp, seconds (NaN if absent)
    channels: Dict[str, np.ndarray]
    extras: List[Any] = field(default_factory=list)  # e.g. ScanData per message
    truncated: bool = False  # capture buffer filled up; later data was dropped

    @property
    def n(self) -> int:
        return int(self.t.size)

    @property
    def duration_s(self) -> float:
        return float(self.t[-1] - self.t[0]) if self.n > 1 else 0.0

    @property
    def rate_hz(self) -> float:
        d = self.duration_s
        return (self.n - 1) / d if d > 0 else 0.0

    def to_csv(self, path: str) -> int:
        names = list(self.channels)
        data = np.column_stack([self.t, self.stamp] + [self.channels[n] for n in names])
        np.savetxt(
            path, data, delimiter=',', header=','.join(['time_s', 'stamp_s'] + names), comments=''
        )
        return self.n


class Capture:
    """Thread-safe, append-only recorder. Stops itself when the limit is reached."""

    def __init__(
        self,
        topic: str,
        spec: Any,
        store_extra: bool = False,
        max_samples: int = 1_000_000,
        max_extras: int = 20_000,
    ) -> None:
        self.topic = topic
        self.spec = spec
        self.store_extra = store_extra
        self.limit = min(max_samples, max_extras) if store_extra else max_samples
        self._t = array.array('d')
        self._stamp = array.array('d')
        self._ch = {name: array.array('d') for name in spec.channels}
        self._extras: List[Any] = []
        self._lock = threading.Lock()

    @property
    def n(self) -> int:
        return len(self._t)

    @property
    def full(self) -> bool:
        return self.n >= self.limit

    def append(
        self, t: float, stamp: Optional[float], channels: Dict[str, float], extra: Any = None
    ) -> None:
        with self._lock:
            if self.n >= self.limit:
                return
            self._t.append(t)
            self._stamp.append(NAN if stamp is None else stamp)
            for name, buf in self._ch.items():
                buf.append(float(channels.get(name, NAN)))
            if self.store_extra:
                self._extras.append(extra)

    def snapshot(self) -> CaptureData:
        with self._lock:
            return CaptureData(
                topic=self.topic,
                spec=self.spec,
                t=np.array(self._t, dtype=float),
                stamp=np.array(self._stamp, dtype=float),
                channels={k: np.array(v, dtype=float) for k, v in self._ch.items()},
                extras=list(self._extras),
                truncated=self.n >= self.limit,
            )
