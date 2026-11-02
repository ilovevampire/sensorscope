"""nav_msgs/msg/Odometry"""

from __future__ import annotations

import math

from ._math import quat_to_euler
from .base import SensorSpec, register


def _make_extractor():
    def extract(msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        tw = msg.twist.twist
        _, _, yaw = quat_to_euler(q.x, q.y, q.z, q.w)
        ch = {"x": float(p.x), "y": float(p.y), "yaw_deg": math.degrees(yaw),
              "vx": float(tw.linear.x), "wz": float(tw.angular.z)}
        return ch, None

    return extract


ODOM = register(SensorSpec(
    msg_type="nav_msgs/msg/Odometry",
    label="Odometry",
    groups={
        "Position (m)": ("x", "y"),
        "Yaw (deg)": ("yaw_deg",),
        "Linear velocity (m/s)": ("vx",),
        "Angular velocity (rad/s)": ("wz",),
    },
    make_extractor=_make_extractor,
    view="track",
    view_channels=("x", "y"),
))
