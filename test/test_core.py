import math

import numpy as np

from sensorscope.core.buffers import RingBuffer
from sensorscope.core.stats import RateEstimator, summarize
from sensorscope.core.stream import SensorStream
from sensorscope.sensors import REGISTRY


def test_ring_buffer_order_and_wraparound():
    buf = RingBuffer(5)
    for i in range(8):
        buf.append(float(i), float(i * 10))
    t, v = buf.get()
    assert list(t) == [3, 4, 5, 6, 7]
    assert list(v) == [30, 40, 50, 60, 70]


def test_ring_buffer_window_and_clear():
    buf = RingBuffer(100)
    for i in range(50):
        buf.append(i * 0.1, i)
    t, _ = buf.get(window_s=1.0)
    assert t[-1] - t[0] <= 1.0 + 1e-9 and len(t) == 11
    buf.clear()
    assert len(buf) == 0 and buf.get()[0].size == 0


def test_rate_estimator():
    r = RateEstimator()
    for i in range(101):
        r.tick(i * 0.01)
    assert abs(r.rate_hz - 100.0) < 1e-6
    assert r.jitter_ms < 1e-6
    assert r.count == 101


def test_summarize_ignores_nan():
    s = summarize([1.0, 2.0, float("nan"), 3.0])
    assert s["mean"] == 2.0 and s["min"] == 1.0 and s["max"] == 3.0 and s["last"] == 3.0
    assert math.isnan(summarize([float("nan")])["mean"])


def test_stream_push_snapshot_csv(tmp_path):
    stream = SensorStream("/imu/data", REGISTRY["sensor_msgs/msg/Imu"], capacity=100)
    for i in range(10):
        stream.push(i * 0.01, {"ax": float(i), "ay": 0.0})
    snap = stream.snapshot()
    assert set(snap) == set(stream.spec.channels)
    assert len(snap["ax"][0]) == 10 and math.isnan(snap["gz"][1][0])
    assert stream.seconds_since_last() is not None
    out = tmp_path / "imu.csv"
    assert stream.to_csv(str(out)) == 10
    lines = out.read_text().splitlines()
    assert lines[0].startswith("time_s,ax,ay,az") and len(lines) == 11


def test_stream_clears_on_time_jump_back():
    stream = SensorStream("/x", REGISTRY["nav_msgs/msg/Odometry"], capacity=100)
    for t in (1.0, 2.0, 3.0):
        stream.push(t, {"x": t})
    stream.push(0.5, {"x": 0.5})  # e.g. simulation reset
    t, _ = stream.snapshot()["x"]
    assert list(t) == [0.5]
