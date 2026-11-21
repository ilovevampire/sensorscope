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
Run the SensorScope GUI.

Use ``ros2 run sensorscope sensorscope`` or ``ros2 launch sensorscope sensorscope.launch.py``.
"""

from __future__ import annotations

import signal
import sys


def main(argv=None) -> None:
    argv = list(sys.argv if argv is None else argv)

    try:
        import rclpy  # noqa: F401
        from rclpy.utilities import remove_ros_args
    except ImportError:
        sys.exit('rclpy not found. Source ROS first:  source /opt/ros/jazzy/setup.bash')
    try:
        import pyqtgraph  # noqa: F401
        from PySide6 import QtCore, QtWidgets
    except ImportError as exc:
        sys.exit(
            f'SensorScope needs PySide6 and pyqtgraph ({exc}).\n'
            'See docs/SETUP.md: pip install PySide6 pyqtgraph'
        )

    from .ros.runner import RosRunner
    from .ui.main_window import MainWindow
    from .ui.theme import apply_dark_theme

    runner = RosRunner(argv)
    runner.start()

    app = QtWidgets.QApplication(remove_ros_args(argv))
    apply_dark_theme(app)
    window = MainWindow(runner)
    window.show()

    # Let Ctrl+C in the terminal close the window cleanly: Qt's event loop
    # blocks Python signal handlers unless a timer wakes the interpreter.
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    wake = QtCore.QTimer()
    wake.start(200)
    wake.timeout.connect(lambda: None)

    code = app.exec()
    runner.stop()
    sys.exit(code)


if __name__ == '__main__':
    main()
