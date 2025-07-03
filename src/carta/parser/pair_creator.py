"""Create prompt-response pairs from conversation nodes."""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def create_pairs(nodes: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract user-assistant message pairs from node tree."""
    pairs = []

    for node_id, node in nodes.items():
        if not node or 'message' not in node:
            continue

        # Safe role extraction
        author_role = node.get('message', {}).get('author', {}).get('role')
        if author_role != 'user':
            continue

        for child_id in node.get('children_ids', []):
            if child_id not in nodes:
                continue

            child_node = nodes[child_id]
            child_author_role = child_node.get('message', {}).get('author', {}).get('role')
            if child_author_role != 'assistant':
                continue

            is_mainline = (
                node.get('derived', {}).get('is_mainline', False) and 
                child_node.get('derived', {}).get('is_mainline', False)
            )

            pairs.append({
                'id': f"{node_id}_{child_id}",
                'prompt_id': node_id,
                'response_id': child_id,
                'is_mainline': is_mainline,
                'is_alternate': not is_mainline,
                'turn_number': child_node.get('derived', {}).get('turn_number', 0) // 2,
                'branch_depth': child_node.get('derived', {}).get('branch_depth', 0),
                'path_from_root': node.get('derived', {}).get('path_from_root', [])
            })

    return pairs
