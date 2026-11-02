"""Sensor plugin interface: a SensorSpec describes how to read one message type.

To add a new sensor, create a module that builds a ``SensorSpec`` and calls
``register(spec)``, then import that module in ``sensors/__init__.py``.
Nothing here imports ROS: extractors only read attributes of the message, so
they can be unit-tested with plain ``SimpleNamespace`` objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

# An extractor turns one ROS message into (scalar channels, optional extra payload).
Extractor = Callable[[Any], Tuple[Dict[str, float], Any]]


@dataclass(frozen=True, eq=False)
class SensorSpec:
    msg_type: str                           # e.g. "sensor_msgs/msg/Imu"
    label: str                              # short name for tabs, e.g. "IMU"
    groups: Dict[str, Tuple[str, ...]]      # plot title -> channels drawn in it
    make_extractor: Callable[[], Extractor]  # factory: one fresh extractor per topic
    view: Optional[str] = None              # special side view: "scan" or "track"
    view_channels: Tuple[str, ...] = ()     # (x, y) channels for the "track" view

    @property
    def channels(self) -> Tuple[str, ...]:
        seen = []
        for chans in self.groups.values():
            for c in chans:
                if c not in seen:
                    seen.append(c)
        return tuple(seen)


REGISTRY: Dict[str, SensorSpec] = {}


def register(spec: SensorSpec) -> SensorSpec:
    REGISTRY[spec.msg_type] = spec
    return spec


def get_spec(msg_type: str) -> Optional[SensorSpec]:
    return REGISTRY.get(msg_type)
