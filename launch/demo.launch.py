"""One-command demo: synthetic sensors + SensorScope."""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(package="sensorscope", executable="fake_sensors", output="screen"),
        Node(package="sensorscope", executable="sensorscope", name="sensorscope", output="screen"),
    ])
