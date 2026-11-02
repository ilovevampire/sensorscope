"""Sensor plugins. Importing this package registers every built-in sensor."""

from .base import REGISTRY, SensorSpec, get_spec, register  # noqa: F401
from . import gps, imu, lidar, odom  # noqa: F401  (imported for registration)
