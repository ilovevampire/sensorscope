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

"""Read sensor_msgs/msg/LaserScan messages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np

from .base import register, SensorSpec

NAN = float('nan')


@dataclass
class ScanData:
    """Compact copy of one scan (float32 ranges), kept as the stream's extra payload."""

    ranges: np.ndarray
    angle_min: float
    angle_increment: float
    range_min: float
    range_max: float

    @property
    def angles(self) -> np.ndarray:
        return self.angle_min + np.arange(self.ranges.size) * self.angle_increment

    def valid_mask(self) -> np.ndarray:
        r = self.ranges
        return np.isfinite(r) & (r >= self.range_min) & (r <= self.range_max)

    def xy(self) -> Tuple[np.ndarray, np.ndarray]:
        """Cartesian coordinates (sensor frame) of the valid returns."""
        ok = self.valid_mask()
        r, a = self.ranges[ok].astype(float), self.angles[ok]
        return r * np.cos(a), r * np.sin(a)


def _make_extractor():
    def extract(msg):
        r = np.asarray(msg.ranges, dtype=np.float32)
        scan = ScanData(
            r,
            float(msg.angle_min),
            float(msg.angle_increment),
            float(msg.range_min),
            float(msg.range_max),
        )
        valid = scan.valid_mask()
        n = r.size
        ch = {
            'valid_pct': 100.0 * float(valid.sum()) / n if n else 0.0,
            'r_min': NAN,
            'r_mean': NAN,
            'r_max': NAN,
        }
        if valid.any():
            rv = r[valid].astype(float)
            ch['r_min'], ch['r_mean'], ch['r_max'] = (
                float(rv.min()),
                float(rv.mean()),
                float(rv.max()),
            )
        return ch, scan

    return extract


LIDAR = register(
    SensorSpec(
        msg_type='sensor_msgs/msg/LaserScan',
        label='LiDAR',
        groups={
            'Valid returns (%)': ('valid_pct',),
            'Range (m)': ('r_min', 'r_mean', 'r_max'),
        },
        make_extractor=_make_extractor,
        view='scan',
        analysis='lidar',
        capture_extra=True,
    )
)
