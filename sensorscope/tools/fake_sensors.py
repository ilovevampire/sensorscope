"""Publishes synthetic IMU, LiDAR, GPS and odometry data so you can try
SensorScope without any hardware or simulator.

    ros2 run sensorscope fake_sensors

The robot drives a 20 m radius circle at 1 m/s inside an 8 x 6 m "room".
Noise levels and biases are deliberately visible so the stats panel has
something to show (e.g. IMU accel x bias of +0.03 m/s², GPS noise of 1.5 m).
"""

from __future__ import annotations

import math
import random

import rclpy
from nav_msgs.msg import Odometry
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu, LaserScan, NavSatFix, NavSatStatus

EARTH_RADIUS_M = 6378137.0
LAT0, LON0 = 47.3769, 8.5417
RADIUS_M, SPEED_MS = 20.0, 1.0
OMEGA = SPEED_MS / RADIUS_M


def yaw_to_quat(yaw: float):
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


class FakeSensors(Node):
    def __init__(self) -> None:
        super().__init__("fake_sensors")
        self._t0 = self.get_clock().now()
        self._imu_yaw = 0.0
        self._imu_pub = self.create_publisher(Imu, "/imu/data", qos_profile_sensor_data)
        self._scan_pub = self.create_publisher(LaserScan, "/scan", qos_profile_sensor_data)
        self._gps_pub = self.create_publisher(NavSatFix, "/gps/fix", 10)
        self._odom_pub = self.create_publisher(Odometry, "/odom", 10)
        self.create_timer(0.01, self._publish_imu)        # 100 Hz
        self.create_timer(0.1, self._publish_scan)        # 10 Hz
        self.create_timer(0.2, self._publish_gps)         # 5 Hz
        self.create_timer(1.0 / 30.0, self._publish_odom)  # 30 Hz
        self.get_logger().info("Publishing /imu/data /scan /gps/fix /odom")

    def _elapsed(self) -> float:
        return (self.get_clock().now() - self._t0).nanoseconds * 1e-9

    def _circle(self, t: float):
        return RADIUS_M * math.sin(OMEGA * t), RADIUS_M * (1.0 - math.cos(OMEGA * t))

    def _publish_imu(self) -> None:
        t = self._elapsed()
        yaw_rate = 0.2 * math.sin(0.3 * t)
        self._imu_yaw += yaw_rate * 0.01
        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "imu_link"
        msg.linear_acceleration.x = 0.03 + random.gauss(0, 0.05)   # +0.03 bias
        msg.linear_acceleration.y = random.gauss(0, 0.05)
        msg.linear_acceleration.z = 9.81 + random.gauss(0, 0.05)
        msg.angular_velocity.x = random.gauss(0, 0.005)
        msg.angular_velocity.y = random.gauss(0, 0.005)
        msg.angular_velocity.z = yaw_rate + 0.002 + random.gauss(0, 0.005)
        (msg.orientation.x, msg.orientation.y,
         msg.orientation.z, msg.orientation.w) = yaw_to_quat(self._imu_yaw)
        msg.orientation_covariance = [0.01, 0.0, 0.0, 0.0, 0.01, 0.0, 0.0, 0.0, 0.01]
        msg.angular_velocity_covariance = [2.5e-5, 0.0, 0.0, 0.0, 2.5e-5, 0.0, 0.0, 0.0, 2.5e-5]
        msg.linear_acceleration_covariance = [2.5e-3, 0.0, 0.0, 0.0, 2.5e-3, 0.0, 0.0, 0.0, 2.5e-3]
        self._imu_pub.publish(msg)

    def _publish_scan(self) -> None:
        n, half_w, half_h = 360, 4.0, 3.0
        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "laser"
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
            r += random.gauss(0, 0.02)
            ranges.append(float("inf") if random.random() < 0.02 else r)  # 2% dropouts
        msg.ranges = ranges
        self._scan_pub.publish(msg)

    def _publish_gps(self) -> None:
        east, north = self._circle(self._elapsed())
        east += random.gauss(0, 1.5)
        north += random.gauss(0, 1.5)
        msg = NavSatFix()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "gps"
        msg.status.status = NavSatStatus.STATUS_FIX
        msg.status.service = NavSatStatus.SERVICE_GPS
        msg.latitude = LAT0 + math.degrees(north / EARTH_RADIUS_M)
        msg.longitude = LON0 + math.degrees(east / (EARTH_RADIUS_M * math.cos(math.radians(LAT0))))
        msg.altitude = 430.0 + random.gauss(0, 2.5)
        msg.position_covariance = [2.25, 0.0, 0.0, 0.0, 2.25, 0.0, 0.0, 0.0, 6.25]
        msg.position_covariance_type = NavSatFix.COVARIANCE_TYPE_DIAGONAL_KNOWN
        self._gps_pub.publish(msg)

    def _publish_odom(self) -> None:
        t = self._elapsed()
        x, y = self._circle(t)
        msg = Odometry()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "odom"
        msg.child_frame_id = "base_link"
        msg.pose.pose.position.x, msg.pose.pose.position.y = x, y
        (msg.pose.pose.orientation.x, msg.pose.pose.orientation.y,
         msg.pose.pose.orientation.z, msg.pose.pose.orientation.w) = yaw_to_quat(OMEGA * t)
        msg.twist.twist.linear.x = SPEED_MS + random.gauss(0, 0.01)
        msg.twist.twist.angular.z = OMEGA
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


if __name__ == "__main__":
    main()
