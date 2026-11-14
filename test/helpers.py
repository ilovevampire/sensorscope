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

"""Synthetic sensor captures with known ground truth, shared by the tests."""

import math

import numpy as np

from sensorscope.core.capture import CaptureData
from sensorscope.sensors import REGISTRY
from sensorscope.sensors.lidar import ScanData

# Truth used by the IMU generator (same as tools/fake_sensors.py)
FS = 100.0
GYRO_SIGMA, GYRO_K = 0.005, 3e-5
ACC_SIGMA, ACC_K = 0.05, 2e-4


def imu_capture(n=300_000, seed=0, fs=FS, stamps=True):
    rng = np.random.default_rng(seed)
    dt = 1.0 / fs
    t = np.arange(n) * dt
    ch = {name: np.zeros(n) for name in REGISTRY['sensor_msgs/msg/Imu'].channels}
    for name in ('gx', 'gy', 'gz'):
        ch[name] = rng.normal(0, GYRO_SIGMA, n) + np.cumsum(
            rng.normal(0, GYRO_K * math.sqrt(dt), n)
        )
    for name in ('ax', 'ay'):
        ch[name] = rng.normal(0, ACC_SIGMA, n) + np.cumsum(rng.normal(0, ACC_K * math.sqrt(dt), n))
    ch['az'] = (
        9.80665 + rng.normal(0, ACC_SIGMA, n) + np.cumsum(rng.normal(0, ACC_K * math.sqrt(dt), n))
    )
    ch['accel_norm'] = np.sqrt(ch['ax'] ** 2 + ch['ay'] ** 2 + ch['az'] ** 2)
    return CaptureData(
        '/imu/data',
        REGISTRY['sensor_msgs/msg/Imu'],
        t + 1000.0,
        t + 1000.0 - 0.002 if stamps else np.full(n, np.nan),
        ch,
    )


def gps_capture(n=3000, seed=1, sigma=2.5, reported=1.5, phi=0.95, rate=5.0):
    rng = np.random.default_rng(seed)

    def ar1():
        x = np.zeros(n)
        w = rng.normal(size=n)
        for k in range(1, n):
            x[k] = phi * x[k - 1] + math.sqrt(1 - phi**2) * w[k]
        return sigma * x

    t = np.arange(n) / rate
    ch = {
        'east': ar1(),
        'north': ar1(),
        'alt': 430 + rng.normal(0, 2.5, n),
        'h_std': np.full(n, reported),
        'status': np.zeros(n),
    }
    return CaptureData('/gps/fix', REGISTRY['sensor_msgs/msg/NavSatFix'], t, t.copy(), ch)


def lidar_capture(
    n_scans=60, seed=2, sigma=0.02, dropout=0.02, n_beams=360, half_w=4.0, half_h=3.0
):
    rng = np.random.default_rng(seed)
    ang = -math.pi + np.arange(n_beams) * (2 * math.pi / n_beams)
    dx, dy = np.abs(np.cos(ang)), np.abs(np.sin(ang))
    true_r = np.minimum(
        np.where(dx > 1e-9, half_w / np.maximum(dx, 1e-9), np.inf),
        np.where(dy > 1e-9, half_h / np.maximum(dy, 1e-9), np.inf),
    )
    scans = []
    for _ in range(n_scans):
        r = true_r + rng.normal(0, sigma, n_beams)
        r[rng.random(n_beams) < dropout] = np.inf
        scans.append(ScanData(r.astype(np.float32), -math.pi, 2 * math.pi / n_beams, 0.12, 12.0))
    t = np.arange(n_scans) * 0.1
    spec = REGISTRY['sensor_msgs/msg/LaserScan']
    ch = {c: np.zeros(n_scans) for c in spec.channels}
    return CaptureData('/scan', spec, t, t.copy(), ch, scans)


def feed(stream, cap, start_capture=True):
    """Push a synthetic CaptureData through a SensorStream (exercises the live path)."""
    if start_capture:
        stream.start_capture()
    names = list(cap.channels)
    for i in range(cap.n):
        stream.push(
            float(cap.t[i]),
            {n: float(cap.channels[n][i]) for n in names},
            cap.extras[i] if cap.extras else None,
            float(cap.stamp[i]),
        )
    stream.stop_capture()
