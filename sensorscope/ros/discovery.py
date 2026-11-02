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
