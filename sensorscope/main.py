"""Entry point: ``ros2 run sensorscope sensorscope`` or ``ros2 launch sensorscope sensorscope.launch.py``."""

from __future__ import annotations

import signal
import sys


def main(argv=None) -> None:
    argv = list(sys.argv if argv is None else argv)

    try:
        import rclpy  # noqa: F401
        from rclpy.utilities import remove_ros_args
    except ImportError:
        sys.exit("rclpy not found. Source ROS first:  source /opt/ros/jazzy/setup.bash")
    try:
        from PySide6 import QtCore, QtWidgets
        import pyqtgraph  # noqa: F401
    except ImportError as exc:
        sys.exit(f"SensorScope needs PySide6 and pyqtgraph ({exc}).\n"
                 "See docs/SETUP.md: pip install PySide6 pyqtgraph")

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


if __name__ == "__main__":
    main()
