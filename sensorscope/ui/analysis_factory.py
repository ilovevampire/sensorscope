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

"""Maps SensorSpec.analysis ("imu", "lidar", "gps") to its Analysis tab class."""

from __future__ import annotations

from typing import Optional

from PySide6 import QtWidgets

from .gps_analysis import GpsAnalysisTab
from .imu_analysis import ImuAnalysisTab
from .lidar_analysis import LidarAnalysisTab

_TABS = {'imu': ImuAnalysisTab, 'lidar': LidarAnalysisTab, 'gps': GpsAnalysisTab}


def make_analysis_tab(stream) -> Optional[QtWidgets.QWidget]:
    cls = _TABS.get(stream.spec.analysis or '')
    return cls(stream) if cls else None
