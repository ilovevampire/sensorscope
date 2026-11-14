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

import numpy as np

from sensorscope.core.capture import Capture
from sensorscope.core.stream import SensorStream
from sensorscope.sensors import REGISTRY


def test_capture_append_snapshot_and_limit(tmp_path):
    spec = REGISTRY['nav_msgs/msg/Odometry']
    cap = Capture('/odom', spec, max_samples=5)
    for i in range(8):
        cap.append(i * 0.1, i * 0.1 - 0.01, {'x': float(i)})
    data = cap.snapshot()
    assert data.n == 5 and cap.full
    assert list(data.channels['x']) == [0, 1, 2, 3, 4]
    assert np.isnan(data.channels['y']).all()  # missing channel -> NaN
    assert data.rate_hz == 10.0 and data.duration_s == 0.4
    assert data.to_csv(str(tmp_path / 'c.csv')) == 5


def test_stream_capture_lifecycle():
    spec = REGISTRY['sensor_msgs/msg/LaserScan']
    stream = SensorStream('/scan', spec)
    stream.push(0.0, {'valid_pct': 90.0}, extra='scan0')  # before capture: ignored
    assert stream.capture_snapshot() is None
    stream.start_capture()
    for i in range(1, 4):
        stream.push(i * 0.1, {'valid_pct': 90.0 + i}, extra=f'scan{i}', stamp=i * 0.1)
    stream.stop_capture()
    stream.push(0.9, {'valid_pct': 0.0}, extra='late')  # after stop: ignored
    data = stream.capture_snapshot()
    assert data.n == 3 and data.extras == ['scan1', 'scan2', 'scan3']  # lidar spec stores extras
    assert list(data.channels['valid_pct']) == [91.0, 92.0, 93.0]
    stream.start_capture()  # a new capture starts fresh
    assert stream.capture_snapshot().n == 0
