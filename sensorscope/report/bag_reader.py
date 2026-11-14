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

"""Read supported sensor topics from a rosbag2 into CaptureData (needs ROS)."""

from __future__ import annotations

from typing import List, Optional, Sequence

from ..core.capture import Capture, CaptureData
from ..sensors import REGISTRY
from ..sensors._math import header_stamp_s


def read_captures(path: str, topics: Optional[Sequence[str]] = None) -> List[CaptureData]:
    """
    Return one CaptureData per supported topic found in the bag.

    Time axis is the bag's log time. Header stamps are kept separately so
    timing analysis can compare them.
    """
    try:
        import rosbag2_py
        from rclpy.serialization import deserialize_message
        from rosidl_runtime_py.utilities import get_message
    except ImportError as exc:
        raise RuntimeError(
            'rosbag2_py not found. Source ROS first: ' 'source /opt/ros/jazzy/setup.bash'
        ) from exc

    reader = rosbag2_py.SequentialReader()
    reader.open(
        rosbag2_py.StorageOptions(uri=str(path)),
        rosbag2_py.ConverterOptions(
            input_serialization_format='cdr', output_serialization_format='cdr'
        ),
    )
    types = {t.name: t.type for t in reader.get_all_topics_and_types()}
    wanted = [n for n, ty in types.items() if ty in REGISTRY and (not topics or n in topics)]
    if not wanted:
        found = ', '.join(sorted(types)) or 'none'
        raise RuntimeError(
            'No supported sensor topics in this bag '
            f'(Imu, LaserScan, NavSatFix, Odometry). Topics found: {found}'
        )
    reader.set_filter(rosbag2_py.StorageFilter(topics=wanted))

    classes = {n: get_message(types[n]) for n in wanted}
    extractors = {n: REGISTRY[types[n]].make_extractor() for n in wanted}
    caps = {
        n: Capture(
            n,
            REGISTRY[types[n]],
            store_extra=REGISTRY[types[n]].capture_extra,
            max_samples=5_000_000,
        )
        for n in wanted
    }
    while reader.has_next():
        topic, data, t_ns = reader.read_next()
        msg = deserialize_message(data, classes[topic])
        channels, extra = extractors[topic](msg)
        caps[topic].append(t_ns * 1e-9, header_stamp_s(msg), channels, extra)
    return [c.snapshot() for c in caps.values() if c.n > 0]
