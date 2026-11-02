import math
from types import SimpleNamespace as NS

import numpy as np

from sensorscope.sensors import REGISTRY


def v3(x=0.0, y=0.0, z=0.0):
    return NS(x=x, y=y, z=z)


def test_registry_has_builtin_sensors():
    assert set(REGISTRY) >= {
        "sensor_msgs/msg/Imu", "sensor_msgs/msg/LaserScan",
        "sensor_msgs/msg/NavSatFix", "nav_msgs/msg/Odometry",
    }
    for spec in REGISTRY.values():
        assert spec.channels  # every sensor exposes at least one channel


def test_imu_extractor_with_and_without_orientation():
    extract = REGISTRY["sensor_msgs/msg/Imu"].make_extractor()
    yaw = math.radians(90)
    msg = NS(linear_acceleration=v3(0, 0, 9.81), angular_velocity=v3(0.1, 0, 0),
             orientation=NS(x=0.0, y=0.0, z=math.sin(yaw / 2), w=math.cos(yaw / 2)),
             orientation_covariance=[0.01] + [0.0] * 8)
    ch, _ = extract(msg)
    assert abs(ch["accel_norm"] - 9.81) < 1e-9 and abs(ch["yaw"] - 90.0) < 1e-6
    msg.orientation_covariance = [-1.0] + [0.0] * 8
    ch, _ = extract(msg)
    assert math.isnan(ch["yaw"])


def test_lidar_extractor_valid_ratio():
    extract = REGISTRY["sensor_msgs/msg/LaserScan"].make_extractor()
    msg = NS(ranges=[1.0, 2.0, float("inf"), 50.0], range_min=0.1, range_max=10.0,
             angle_min=0.0, angle_increment=math.pi / 2)
    ch, (xs, ys) = extract(msg)
    assert ch["valid_pct"] == 50.0 and ch["r_min"] == 1.0 and ch["r_max"] == 2.0
    assert np.allclose(xs, [1.0, 0.0], atol=1e-9) and np.allclose(ys, [0.0, 2.0], atol=1e-9)


def test_gps_extractor_local_enu_and_no_fix():
    extract = REGISTRY["sensor_msgs/msg/NavSatFix"].make_extractor()

    def fix(lat, lon, status=0):
        return NS(latitude=lat, longitude=lon, altitude=100.0, status=NS(status=status),
                  position_covariance=[4.0, 0, 0, 0, 4.0, 0, 0, 0, 9.0],
                  position_covariance_type=2)

    ch, _ = extract(fix(10.0, 20.0))
    assert ch["east"] == 0.0 and ch["north"] == 0.0 and ch["h_std"] == 2.0
    ch, _ = extract(fix(10.0 + 1e-4, 20.0))  # ~11.1 m north
    assert 11.0 < ch["north"] < 11.3 and abs(ch["east"]) < 1e-6
    ch, _ = extract(fix(float("nan"), float("nan"), status=-1))
    assert math.isnan(ch["east"]) and ch["status"] == -1.0


def test_odom_extractor():
    extract = REGISTRY["nav_msgs/msg/Odometry"].make_extractor()
    msg = NS(pose=NS(pose=NS(position=v3(1.0, 2.0), orientation=NS(x=0.0, y=0.0, z=0.0, w=1.0))),
             twist=NS(twist=NS(linear=v3(0.5), angular=v3(z=0.1))))
    ch, _ = extract(msg)
    assert (ch["x"], ch["y"], ch["vx"], ch["wz"]) == (1.0, 2.0, 0.5, 0.1) and ch["yaw_deg"] == 0.0
