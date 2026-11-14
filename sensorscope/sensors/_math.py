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

"""Small math helpers shared by sensor extractors."""

from __future__ import annotations

import math
from typing import Tuple


def quat_to_euler(x: float, y: float, z: float, w: float) -> Tuple[float, float, float]:
    """Quaternion -> (roll, pitch, yaw) in radians (ZYX convention)."""
    roll = math.atan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y))
    sinp = max(-1.0, min(1.0, 2.0 * (w * y - z * x)))
    pitch = math.asin(sinp)
    yaw = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
    return roll, pitch, yaw


def header_stamp_s(msg):
    """Header stamp in seconds, or None if the message has no (or a zero) stamp."""
    header = getattr(msg, 'header', None)
    if header is None:
        return None
    s = header.stamp.sec + header.stamp.nanosec * 1e-9
    return s if s > 0.0 else None
