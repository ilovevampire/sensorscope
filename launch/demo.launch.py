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
One-command demo: synthetic sensors + SensorScope.

    ros2 launch sensorscope demo.launch.py                # robot driving a circle
    ros2 launch sensorscope demo.launch.py static:=true   # still sensors, for the Analysis tabs
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'static',
                default_value='false',
                description='Publish still sensors (needed for meaningful Analysis)',
            ),
            Node(
                package='sensorscope',
                executable='fake_sensors',
                output='screen',
                parameters=[{'static': LaunchConfiguration('static')}],
            ),
            Node(
                package='sensorscope',
                executable='sensorscope',
                name='sensorscope',
                output='screen',
            ),
        ]
    )
