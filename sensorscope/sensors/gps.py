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

"""Read sensor_msgs/msg/NavSatFix messages."""

from __future__ import annotations

import math

from .base import register, SensorSpec

NAN = float('nan')
EARTH_RADIUS_M = 6378137.0


def _make_extractor():
    origin = {}  # first valid fix, used as the local ENU origin

    def extract(msg):
        lat, lon = float(msg.latitude), float(msg.longitude)
        has_fix = msg.status.status >= 0 and math.isfinite(lat) and math.isfinite(lon)
        east = north = NAN
        if has_fix:
            if not origin:
                origin['lat'], origin['lon'] = lat, lon
            # Equirectangular approximation: accurate to cm over a few km.
            north = math.radians(lat - origin['lat']) * EARTH_RADIUS_M
            east = (
                math.radians(lon - origin['lon'])
                * EARTH_RADIUS_M
                * math.cos(math.radians(origin['lat']))
            )
        h_std = NAN
        if msg.position_covariance_type != 0:  # 0 = COVARIANCE_TYPE_UNKNOWN
            cov = msg.position_covariance
            h_std = math.sqrt(max((cov[0] + cov[4]) / 2.0, 0.0))
        ch = {
            'east': east,
            'north': north,
            'alt': float(msg.altitude),
            'h_std': h_std,
            'status': float(msg.status.status),
        }
        return ch, None

    return extract


GPS = register(
    SensorSpec(
        msg_type='sensor_msgs/msg/NavSatFix',
        label='GPS',
        groups={
            'Local position from first fix (m)': ('east', 'north'),
            'Altitude (m)': ('alt',),
            'Reported horizontal std (m)': ('h_std',),
            'Fix status (-1 none, 0 fix, 1 SBAS, 2 GBAS)': ('status',),
        },
        make_extractor=_make_extractor,
        view='track',
        view_channels=('east', 'north'),
        analysis='gps',
    )
)
