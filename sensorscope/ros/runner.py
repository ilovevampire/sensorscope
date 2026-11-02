"""RosRunner: owns rclpy init/shutdown and spins the node on a background thread."""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

import rclpy
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor

from ..core.stream import SensorStream
from .node import SensorScopeNode


class RosRunner:
    """Qt owns the main thread, so ROS spins in the background.

    Exposes ``get_streams()`` so the GUI only depends on that one method.
    """

    def __init__(self, args: Optional[List[str]] = None) -> None:
        self._args = args
        self.node: Optional[SensorScopeNode] = None
        self._executor: Optional[SingleThreadedExecutor] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        rclpy.init(args=self._args)
        self.node = SensorScopeNode()
        self._executor = SingleThreadedExecutor()
        self._executor.add_node(self.node)
        self._thread = threading.Thread(target=self._spin, name="sensorscope-ros", daemon=True)
        self._thread.start()

    def _spin(self) -> None:
        try:
            self._executor.spin()
        except ExternalShutdownException:
            pass

    def get_streams(self) -> Dict[str, SensorStream]:
        return self.node.get_streams() if self.node else {}

    def stop(self) -> None:
        if self._executor is not None:
            self._executor.shutdown()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if self.node is not None:
            self.node.destroy_node()
        rclpy.try_shutdown()
