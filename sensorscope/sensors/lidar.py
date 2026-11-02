"""sensor_msgs/msg/LaserScan"""

from __future__ import annotations

import numpy as np

from .base import SensorSpec, register

NAN = float("nan")


def _make_extractor():
    def extract(msg):
        r = np.asarray(msg.ranges, dtype=float)
        n = r.size
        valid = np.isfinite(r) & (r >= msg.range_min) & (r <= msg.range_max)
        ch = {"valid_pct": 100.0 * float(valid.sum()) / n if n else 0.0,
              "r_min": NAN, "r_mean": NAN, "r_max": NAN}
        if valid.any():
            rv = r[valid]
            ch["r_min"], ch["r_mean"], ch["r_max"] = float(rv.min()), float(rv.mean()), float(rv.max())
            ang = msg.angle_min + np.arange(n)[valid] * msg.angle_increment
            extra = (rv * np.cos(ang), rv * np.sin(ang))
        else:
            extra = (np.empty(0), np.empty(0))
        return ch, extra

    return extract


LIDAR = register(SensorSpec(
    msg_type="sensor_msgs/msg/LaserScan",
    label="LiDAR",
    groups={
        "Valid returns (%)": ("valid_pct",),
        "Range (m)": ("r_min", "r_mean", "r_max"),
    },
    make_extractor=_make_extractor,
    view="scan",
))
