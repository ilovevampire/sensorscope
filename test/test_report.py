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

from types import SimpleNamespace as NS

import numpy as np
import pytest

pytest.importorskip('matplotlib')

from helpers import gps_capture, imu_capture, lidar_capture  # noqa: E402,I100

from sensorscope.core.capture import CaptureData  # noqa: E402
from sensorscope.report.builder import build_report  # noqa: E402
from sensorscope.sensors import REGISTRY  # noqa: E402
from sensorscope.sensors._math import header_stamp_s  # noqa: E402


def odom_capture(n=300):
    t = np.arange(n) / 30.0
    spec = REGISTRY['nav_msgs/msg/Odometry']
    ch = {
        'x': 20 * np.sin(0.05 * t),
        'y': 20 * (1 - np.cos(0.05 * t)),
        'yaw_deg': 2.9 * t,
        'vx': np.ones(n),
        'wz': np.full(n, 0.05),
    }
    return CaptureData('/odom', spec, t, t.copy(), ch)


def test_header_stamp_helper():
    assert header_stamp_s(NS(header=NS(stamp=NS(sec=12, nanosec=500_000_000)))) == 12.5
    assert header_stamp_s(NS(header=NS(stamp=NS(sec=0, nanosec=0)))) is None
    assert header_stamp_s(NS()) is None


def test_full_report_contains_every_section():
    caps = [imu_capture(n=60_000), lidar_capture(n_scans=40), gps_capture(n=1500), odom_capture()]
    doc = build_report(caps, 'Test report', source='/tmp/bag')
    assert doc.startswith('<!doctype html>') and 'Test report' in doc
    for needle in (
        'Allan deviation',
        'Kalibr YAML',
        'gyroscope_noise_density',
        'Gazebo noise',
        'Wall distance',
        'CEP95',
        'Optimistic covariance',
        'Odometry track',
        'Timing',
        'Channel statistics',
    ):
        assert needle in doc, needle
    assert doc.count('data:image/png;base64,') == 5
    assert 'nan' not in doc.split('<h3>Kalibr YAML</h3>')[1].split('</pre>')[0]


def test_report_survives_short_captures():
    short = imu_capture(n=100)  # too short for analysis
    doc = build_report([short, gps_capture(n=10)], 'Short')
    assert doc.count('Analysis skipped') == 2
    assert 'Channel statistics' in doc


def test_report_marks_truncated_capture():
    cap = imu_capture(n=2000)
    cap.truncated = True
    assert 'buffer filled up' in build_report([cap])
