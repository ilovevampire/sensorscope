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

"""
Publish synthetic IMU, LiDAR, GPS and odometry data for trying SensorScope.

No hardware or simulator is needed.

    ros2 run sensorscope fake_sensors                              # robot driving a circle
    ros2 run sensorscope fake_sensors --ros-args -p static:=true   # everything standing still

Use ``static:=true`` to try the Analysis tabs: they expect a still sensor.

Ground truth injected (so you can check what the Analysis tabs report):

  IMU    100 Hz   gyro  white noise sigma 0.005 rad/s     -> N = 5.0e-4 rad/s/sqrt(Hz)
                  gyro  bias random walk K = 3e-5 rad/s^2/sqrt(Hz)
                  accel white noise sigma 0.05 m/s^2      -> N = 5.0e-3 m/s^2/sqrt(Hz)
                  accel bias random walk K = 2e-4 m/s^3/sqrt(Hz); ax has a +0.03 offset
  LiDAR   10 Hz   8 x 6 m room, range noise 0.02 m (0.05 m for beams at 100..120 deg),
                  2 % random dropouts
  GPS      5 Hz   position error sigma 2.5 m, time-correlated (AR(1), about 4 s), but the
                  message reports only 1.5 m: an "optimistic covariance" for you to find
  Odom    30 Hz   perfect circle (20 m radius, 1 m/s), tiny velocity noise
"""

from __future__ import annotations

import math
import random

from nav_msgs.msg import Odometry
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu, LaserScan, NavSatFix, NavSatStatus

EARTH_RADIUS_M = 6378137.0
LAT0, LON0 = 47.3769, 8.5417
RADIUS_M, SPEED_MS = 20.0, 1.0
OMEGA = SPEED_MS / RADIUS_M

IMU_DT = 0.01
GYRO_SIGMA, GYRO_K = 0.005, 3e-5
ACCEL_SIGMA, ACCEL_K = 0.05, 2e-4
GPS_TRUE_SIGMA, GPS_REPORTED_SIGMA, GPS_PHI = 2.5, 1.5, 0.95


def yaw_to_quat(yaw: float):
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


class FakeSensors(Node):
    """ROS node that publishes the synthetic sensor topics."""

    def __init__(self) -> None:
        super().__init__('fake_sensors')
        self.declare_parameter('static', False)
        self._static = bool(self.get_parameter('static').value)
        self._t0 = self.get_clock().now()
        self._imu_yaw = 0.0
        self._gyro_bias = [0.0, 0.0, 0.0]
        self._accel_bias = [0.0, 0.0, 0.0]
        self._gps_err = [0.0, 0.0]
        self._imu_pub = self.create_publisher(Imu, '/imu/data', qos_profile_sensor_data)
        self._scan_pub = self.create_publisher(LaserScan, '/scan', qos_profile_sensor_data)
        self._gps_pub = self.create_publisher(NavSatFix, '/gps/fix', 10)
        self._odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.create_timer(IMU_DT, self._publish_imu)  # 100 Hz
        self.create_timer(0.1, self._publish_scan)  # 10 Hz
        self.create_timer(0.2, self._publish_gps)  # 5 Hz
        self.create_timer(1.0 / 30.0, self._publish_odom)  # 30 Hz
        mode = 'STATIC (use the Analysis tabs)' if self._static else 'moving'
        self.get_logger().info(f'Publishing /imu/data /scan /gps/fix /odom, {mode}')

    def _elapsed(self) -> float:
        return (self.get_clock().now() - self._t0).nanoseconds * 1e-9

    def _circle(self, t: float):
        if self._static:
            return 0.0, 0.0
        return RADIUS_M * math.sin(OMEGA * t), RADIUS_M * (1.0 - math.cos(OMEGA * t))

    def _publish_imu(self) -> None:
        t = self._elapsed()
        yaw_rate = 0.0 if self._static else 0.2 * math.sin(0.3 * t)
        self._imu_yaw += yaw_rate * IMU_DT
        for i in range(3):  # bias random walks
            self._gyro_bias[i] += random.gauss(0, GYRO_K * math.sqrt(IMU_DT))
            self._accel_bias[i] += random.gauss(0, ACCEL_K * math.sqrt(IMU_DT))
        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'imu_link'
        msg.linear_acceleration.x = 0.03 + self._accel_bias[0] + random.gauss(0, ACCEL_SIGMA)
        msg.linear_acceleration.y = self._accel_bias[1] + random.gauss(0, ACCEL_SIGMA)
        msg.linear_acceleration.z = 9.80665 + self._accel_bias[2] + random.gauss(0, ACCEL_SIGMA)
        msg.angular_velocity.x = self._gyro_bias[0] + random.gauss(0, GYRO_SIGMA)
        msg.angular_velocity.y = self._gyro_bias[1] + random.gauss(0, GYRO_SIGMA)
        msg.angular_velocity.z = yaw_rate + self._gyro_bias[2] + random.gauss(0, GYRO_SIGMA)
        msg.orientation.x, msg.orientation.y, msg.orientation.z, msg.orientation.w = yaw_to_quat(
            self._imu_yaw
        )
        msg.orientation_covariance = [0.01, 0.0, 0.0, 0.0, 0.01, 0.0, 0.0, 0.0, 0.01]
        msg.angular_velocity_covariance = [
            GYRO_SIGMA**2,
            0.0,
            0.0,
            0.0,
            GYRO_SIGMA**2,
            0.0,
            0.0,
            0.0,
            GYRO_SIGMA**2,
        ]
        msg.linear_acceleration_covariance = [
            ACCEL_SIGMA**2,
            0.0,
            0.0,
            0.0,
            ACCEL_SIGMA**2,
            0.0,
            0.0,
            0.0,
            ACCEL_SIGMA**2,
        ]
        self._imu_pub.publish(msg)

    def _publish_scan(self) -> None:
        n, half_w, half_h = 360, 4.0, 3.0
        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'laser'
        msg.angle_min = -math.pi
        msg.angle_increment = 2.0 * math.pi / n
        msg.angle_max = msg.angle_min + (n - 1) * msg.angle_increment
        msg.scan_time = 0.1
        msg.range_min, msg.range_max = 0.12, 12.0
        ranges = []
        for i in range(n):
            a = msg.angle_min + i * msg.angle_increment
            dx, dy = abs(math.cos(a)), abs(math.sin(a))
            r = min(half_w / dx if dx > 1e-9 else math.inf, half_h / dy if dy > 1e-9 else math.inf)
            sigma = 0.05 if 100.0 <= math.degrees(a) <= 120.0 else 0.02  # a noisier sector
            r += random.gauss(0, sigma)
            ranges.append(float('inf') if random.random() < 0.02 else r)  # 2 % dropouts
        msg.ranges = ranges
        self._scan_pub.publish(msg)

    def _publish_gps(self) -> None:
        east, north = self._circle(self._elapsed())
        for i in range(2):  # time-correlated error, stationary std = GPS_TRUE_SIGMA
            self._gps_err[i] = GPS_PHI * self._gps_err[i] + math.sqrt(
                1.0 - GPS_PHI**2
            ) * random.gauss(0, GPS_TRUE_SIGMA)
        east += self._gps_err[0]
        north += self._gps_err[1]
        msg = NavSatFix()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'gps'
        msg.status.status = NavSatStatus.STATUS_FIX
        msg.status.service = NavSatStatus.SERVICE_GPS
        msg.latitude = LAT0 + math.degrees(north / EARTH_RADIUS_M)
        msg.longitude = LON0 + math.degrees(east / (EARTH_RADIUS_M * math.cos(math.radians(LAT0))))
        msg.altitude = 430.0 + random.gauss(0, 2.5)
        v = GPS_REPORTED_SIGMA**2
        msg.position_covariance = [v, 0.0, 0.0, 0.0, v, 0.0, 0.0, 0.0, 6.25]
        msg.position_covariance_type = NavSatFix.COVARIANCE_TYPE_DIAGONAL_KNOWN
        self._gps_pub.publish(msg)

    def _publish_odom(self) -> None:
        t = self._elapsed()
        x, y = self._circle(t)
        yaw = 0.0 if self._static else OMEGA * t
        msg = Odometry()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'odom'
        msg.child_frame_id = 'base_link'
        msg.pose.pose.position.x, msg.pose.pose.position.y = x, y
        (
            msg.pose.pose.orientation.x,
            msg.pose.pose.orientation.y,
            msg.pose.pose.orientation.z,
            msg.pose.pose.orientation.w,
        ) = yaw_to_quat(yaw)
        msg.twist.twist.linear.x = 0.0 if self._static else SPEED_MS + random.gauss(0, 0.01)
        msg.twist.twist.angular.z = 0.0 if self._static else OMEGA
        self._odom_pub.publish(msg)


def main() -> None:
    rclpy.init()
    node = FakeSensors()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
