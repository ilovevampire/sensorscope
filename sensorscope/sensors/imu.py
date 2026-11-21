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

"""Read sensor_msgs/msg/Imu messages."""

from __future__ import annotations

import math

from ._math import quat_to_euler
from .base import register, SensorSpec

NAN = float('nan')


def _make_extractor():
    def extract(msg):
        a, g, q = msg.linear_acceleration, msg.angular_velocity, msg.orientation
        ch = {
            'ax': float(a.x),
            'ay': float(a.y),
            'az': float(a.z),
            'accel_norm': math.sqrt(a.x**2 + a.y**2 + a.z**2),
            'gx': float(g.x),
            'gy': float(g.y),
            'gz': float(g.z),
            'roll': NAN,
            'pitch': NAN,
            'yaw': NAN,
        }
        # By REP-145, orientation_covariance[0] == -1 means "no orientation".
        if msg.orientation_covariance[0] != -1.0:
            r, p, y = quat_to_euler(q.x, q.y, q.z, q.w)
            ch['roll'], ch['pitch'], ch['yaw'] = (
                math.degrees(r),
                math.degrees(p),
                math.degrees(y),
            )
        return ch, None

    return extract


IMU = register(
    SensorSpec(
        msg_type='sensor_msgs/msg/Imu',
        label='IMU',
        groups={
            'Acceleration (m/s²)': ('ax', 'ay', 'az'),
            'Acceleration magnitude (m/s²)': ('accel_norm',),
            'Angular velocity (rad/s)': ('gx', 'gy', 'gz'),
            'Orientation (deg)': ('roll', 'pitch', 'yaw'),
        },
        make_extractor=_make_extractor,
        analysis='imu',
    )
)
