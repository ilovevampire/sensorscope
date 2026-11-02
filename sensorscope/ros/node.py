"""SensorScopeNode: discovers sensor topics, subscribes, fills SensorStreams."""

from __future__ import annotations

import functools
import threading
from typing import Dict

from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rosidl_runtime_py.utilities import get_message

from ..core.stream import SensorStream
from ..sensors import REGISTRY
from .discovery import find_supported_topics


class SensorScopeNode(Node):
    """Auto-subscribes to every supported sensor topic, now and as they appear.

    Parameters
    ----------
    buffer_size (int, default 20000): samples kept per channel.
    discovery_period_s (float, default 2.0): how often to look for new topics.
    """

    def __init__(self) -> None:
        super().__init__("sensorscope")
        self.declare_parameter("buffer_size", 20000)
        self.declare_parameter("discovery_period_s", 2.0)
        self._buffer_size = int(self.get_parameter("buffer_size").value)
        period = float(self.get_parameter("discovery_period_s").value)

        self._lock = threading.Lock()
        self._streams: Dict[str, SensorStream] = {}
        self._extractors = {}
        self._subs = {}

        self._discover()
        self.create_timer(period, self._discover)

    # -- public API used by the GUI thread -------------------------------------
    def get_streams(self) -> Dict[str, SensorStream]:
        with self._lock:
            return dict(self._streams)

    # -- internals (ROS thread) -----------------------------------------------
    def _discover(self) -> None:
        for topic, msg_type in find_supported_topics(self, REGISTRY).items():
            if topic in self._subs:
                continue
            spec = REGISTRY[msg_type]
            try:
                msg_cls = get_message(msg_type)
            except (ModuleNotFoundError, AttributeError, ValueError) as exc:
                self.get_logger().warning(f"Cannot load {msg_type} for {topic}: {exc}")
                continue
            stream = SensorStream(topic, spec, self._buffer_size)
            self._extractors[topic] = spec.make_extractor()
            with self._lock:
                self._streams[topic] = stream
            # Best-effort sensor QoS is compatible with both reliable and
            # best-effort publishers, so it works for nearly every driver.
            self._subs[topic] = self.create_subscription(
                msg_cls, topic, functools.partial(self._on_msg, topic), qos_profile_sensor_data)
            self.get_logger().info(f"Monitoring {topic} ({msg_type})")

    def _on_msg(self, topic: str, msg) -> None:
        try:
            channels, extra = self._extractors[topic](msg)
        except Exception as exc:  # noqa: BLE001 - never let one bad message kill the node
            self.get_logger().warning(f"Could not decode message on {topic}: {exc}",
                                      throttle_duration_sec=5.0)
            return
        # Node clock: follows /clock automatically when use_sim_time is true.
        t = self.get_clock().now().nanoseconds * 1e-9
        self._streams[topic].push(t, channels, extra)
