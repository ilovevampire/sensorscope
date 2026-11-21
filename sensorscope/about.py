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

"""Project information shown in the Help menu (no ROS or Qt imports)."""

from . import __version__

NAME = 'SensorScope'
TAGLINE = 'Live visualisation and analysis of ROS 2 sensor data'
VERSION = __version__
AUTHOR = 'Vishal Gaud'
AUTHOR_HANDLE = '@ilovevampire'
AUTHOR_URL = 'https://github.com/ilovevampire'
REPO_URL = 'https://github.com/ilovevampire/sensorscope'
ISSUES_URL = REPO_URL + '/issues'
DOCS_URL = REPO_URL + '/blob/main/docs/ANALYSIS.md'
LICENSE_NAME = 'Apache License 2.0'
COPYRIGHT = 'Copyright © 2026 ' + AUTHOR

THIRD_PARTY = (
    ('PySide6 (Qt for Python)', 'LGPL-3.0', 'https://doc.qt.io/qtforpython-6/'),
    ('pyqtgraph', 'MIT', 'https://www.pyqtgraph.org/'),
    ('NumPy', 'BSD-3-Clause', 'https://numpy.org/'),
    ('Matplotlib (reports)', 'PSF-based', 'https://matplotlib.org/'),
)

QUICK_START = (
    (
        'Start your sensors',
        'Launch your robot, a Gazebo simulation, or play a bag. '
        'SensorScope finds Imu, LaserScan, NavSatFix and Odometry topics by itself.',
    ),
    (
        'Live tab',
        'Scrolling plots and numeric statistics per channel. Use Window to change '
        'the time span, Pause to freeze, Export CSV to save the visible data.',
    ),
    (
        'Analysis tab',
        'IMU, LiDAR and GPS have an Analysis tab. Keep the sensor still, press '
        'Start capture, wait (IMU: 10 minutes or more), then Stop capture.',
    ),
    (
        'Tuning values',
        'On the IMU tab, Copy Kalibr YAML or Copy Gazebo noise puts the '
        'measured noise parameters on the clipboard.',
    ),
    (
        'Offline report',
        'Record a bag, then run: ros2 run sensorscope report my_bag -o report.html',
    ),
    ('No hardware?', 'Run: ros2 launch sensorscope demo.launch.py static:=true'),
)
