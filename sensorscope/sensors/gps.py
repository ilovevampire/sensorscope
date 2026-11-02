"""sensor_msgs/msg/NavSatFix"""

from __future__ import annotations

import math

from .base import SensorSpec, register

NAN = float("nan")
EARTH_RADIUS_M = 6378137.0


def _make_extractor():
    origin = {}  # first valid fix, used as the local ENU origin

    def extract(msg):
        lat, lon = float(msg.latitude), float(msg.longitude)
        has_fix = msg.status.status >= 0 and math.isfinite(lat) and math.isfinite(lon)
        east = north = NAN
        if has_fix:
            if not origin:
                origin["lat"], origin["lon"] = lat, lon
            # Equirectangular approximation: accurate to cm over a few km.
            north = math.radians(lat - origin["lat"]) * EARTH_RADIUS_M
            east = math.radians(lon - origin["lon"]) * EARTH_RADIUS_M * math.cos(math.radians(origin["lat"]))
        h_std = NAN
        if msg.position_covariance_type != 0:  # 0 = COVARIANCE_TYPE_UNKNOWN
            cov = msg.position_covariance
            h_std = math.sqrt(max((cov[0] + cov[4]) / 2.0, 0.0))
        ch = {"east": east, "north": north, "alt": float(msg.altitude),
              "h_std": h_std, "status": float(msg.status.status)}
        return ch, None

    return extract


GPS = register(SensorSpec(
    msg_type="sensor_msgs/msg/NavSatFix",
    label="GPS",
    groups={
        "Local position from first fix (m)": ("east", "north"),
        "Altitude (m)": ("alt",),
        "Reported horizontal std (m)": ("h_std",),
        "Fix status (-1 none, 0 fix, 1 SBAS, 2 GBAS)": ("status",),
    },
    make_extractor=_make_extractor,
    view="track",
    view_channels=("east", "north"),
))
