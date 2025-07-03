"""Path analysis for conversation trees."""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def find_root_nodes(mapping: Dict[str, Any]) -> List[str]:
    """Find root nodes in conversation tree."""
    root_nodes = []
    for node_id, node in mapping.items():
        parent = node.get('parent')
        if parent is None:
            root_nodes.append(node_id)
    return root_nodes


def find_current_node(data: Dict[str, Any], mapping: Dict[str, Any]) -> Optional[str]:
    """Find mainline endpoint node ID."""
    if 'current_node' in data:
        return data['current_node']

    # Fallback to last root node if current_node not specified
    root_nodes = find_root_nodes(mapping)
    return root_nodes[-1] if root_nodes else None


def determine_mainline_path(nodes: Dict[str, Dict[str, Any]], current_node_id: Optional[str]) -> List[str]:
    """Determine mainline path from root to current node."""
    if current_node_id is None or current_node_id not in nodes:
        return []

    # Traverse up from current node to root
    mainline_path = []
    node_id = current_node_id
    while node_id:
        mainline_path.append(node_id)
        parent_id = nodes[node_id].get('parent_id')
        if parent_id is None or parent_id not in nodes:
            break
        node_id = parent_id

    mainline_path.reverse()
    return mainline_path


def compute_path_from_root(nodes: Dict[str, Dict[str, Any]], node_id: str) -> List[str]:
    """Compute path from root to given node."""
    if node_id not in nodes:
        return []

    path = []
    current_id = node_id

    while current_id:
        path.append(current_id)
        parent_id = nodes[current_id].get('parent_id')
        if parent_id is None or parent_id not in nodes:
            break
        current_id = parent_id

        # Prevent infinite loops from circular references
        if current_id in path:
            logger.error(f"Circular reference detected in path: {current_id}")
            break

    path.reverse()
    return path


def find_divergence_point(path: List[str], mainline_path: List[str]) -> Optional[str]:
    """Find last common node before paths diverge."""
    if not path or not mainline_path:
        return None

    last_common = None
    min_length = min(len(path), len(mainline_path))

    for i in range(min_length):
        if path[i] == mainline_path[i]:
            last_common = path[i]
        else:
            break

    return last_common
