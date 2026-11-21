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

"""Find topics whose message type SensorScope knows how to display."""

from __future__ import annotations

from typing import Dict, Mapping


def find_supported_topics(node, registry: Mapping[str, object]) -> Dict[str, str]:
    """Return ``{topic_name: msg_type}`` for every supported topic in the graph."""
    found: Dict[str, str] = {}
    for name, types in node.get_topic_names_and_types():
        for msg_type in types:
            if msg_type in registry:
                found[name] = msg_type
                break
    return found
