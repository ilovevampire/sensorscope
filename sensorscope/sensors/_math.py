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
