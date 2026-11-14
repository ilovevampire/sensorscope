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

"""SensorScopeNode: discovers sensor topics, subscribes, fills SensorStreams."""

from __future__ import annotations

import functools
import threading
from typing import Dict

from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rosidl_runtime_py.utilities import get_message

from .discovery import find_supported_topics
from ..core.stream import SensorStream
from ..sensors import REGISTRY
from ..sensors._math import header_stamp_s


class SensorScopeNode(Node):
    """
    Auto-subscribes to every supported sensor topic, now and as they appear.

    Parameter ``buffer_size`` (int, default 20000) sets the samples kept per channel for the
    live plots. Parameter ``discovery_period_s`` (float, default 2.0) sets how often to look
    for new topics.
    """

    def __init__(self) -> None:
        super().__init__('sensorscope')
        self.declare_parameter('buffer_size', 20000)
        self.declare_parameter('discovery_period_s', 2.0)
        self._buffer_size = int(self.get_parameter('buffer_size').value)
        period = float(self.get_parameter('discovery_period_s').value)

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
                self.get_logger().warning(f'Cannot load {msg_type} for {topic}: {exc}')
                continue
            stream = SensorStream(topic, spec, self._buffer_size)
            self._extractors[topic] = spec.make_extractor()
            with self._lock:
                self._streams[topic] = stream
            # Best-effort sensor QoS is compatible with both reliable and
            # best-effort publishers, so it works for nearly every driver.
            self._subs[topic] = self.create_subscription(
                msg_cls, topic, functools.partial(self._on_msg, topic), qos_profile_sensor_data
            )
            self.get_logger().info(f'Monitoring {topic} ({msg_type})')

    def _on_msg(self, topic: str, msg) -> None:
        try:
            channels, extra = self._extractors[topic](msg)
        except Exception as exc:  # noqa: BLE001 - never let one bad message kill the node
            self.get_logger().warning(
                f'Could not decode message on {topic}: {exc}', throttle_duration_sec=5.0
            )
            return
        # Node clock: follows /clock automatically when use_sim_time is true.
        t = self.get_clock().now().nanoseconds * 1e-9
        self._streams[topic].push(t, channels, extra, stamp=header_stamp_s(msg))
