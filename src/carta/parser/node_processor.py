"""Process conversation tree nodes and extract derived metadata."""

import logging
from typing import Dict, List, Any, Optional, Tuple

from .path_analyzer import determine_mainline_path, compute_path_from_root, find_divergence_point

logger = logging.getLogger(__name__)


def process_nodes(mapping: Dict[str, Any], current_node_id: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """Transform node mapping into processed nodes with derived metadata."""
    nodes = {}

    for node_id, node_data in mapping.items():
        nodes[node_id] = extract_node_data(node_id, node_data)

    mainline_path = determine_mainline_path(nodes, current_node_id)
    mainline_nodes = set(mainline_path)

    for node_id, node in nodes.items():
        path_from_root = compute_path_from_root(nodes, node_id)
        node['derived'] = {
            'path_from_root': path_from_root,
            'is_mainline': node_id in mainline_nodes,
            'is_terminal': not node['children_ids'],
            'siblings_count': count_siblings(nodes, node_id),
            'branch_depth': len(path_from_root) - 1 if path_from_root else 0,
            'is_regeneration': is_regeneration(nodes, node_id),
            'mainline_divergence_point': find_divergence_point(path_from_root, mainline_path) 
                if not node_id in mainline_nodes else None,
            'replaced_node_id': None,
            'semantic_distance_from_parent': None,
            'turn_number': compute_turn_number(nodes, node_id),
            'generation_type': determine_generation_type(nodes, node_id)
        }

    return nodes


def extract_node_data(node_id: str, node_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract node data from raw JSON."""
    message = node_data.get('message', {})
    content = message.get('content', {}) if message else {}

    text, content_type = _extract_content(content)

    metadata = message.get('metadata', {}) if message else {}
    author = message.get('author', {}) if message else {}

    children = node_data.get('children', [])

    return {
        'id': node_id,
        'parent_id': node_data.get('parent'),
        'children_ids': children,
        'message': {
            'author': {
                'role': author.get('role') if author else None
            },
            'content': {
                'text': text,
                'content_type': content_type
            },
            'create_time': message.get('create_time') if message else None
        },
        'metadata': {
            'model_slug': metadata.get('model_slug'),
            'requested_model_slug': metadata.get('requested_model_slug'),
            'is_visually_hidden': metadata.get('is_visually_hidden_from_conversation', False),
            'reasoning_status': metadata.get('reasoning_status'),
            'voice_mode_message': metadata.get('voice_mode_message', False)
        }
    }


def _extract_content(content: Any) -> Tuple[str, str]:
    """Extract text and content type from content field."""
    text = ""
    content_type = 'text'

    if not content:
        return text, content_type

    if isinstance(content, dict):
        content_type = content.get('content_type', 'text')

    # Handle ChatGPT JSON format with 'parts'
    if isinstance(content, dict) and 'parts' in content:
        for part in content.get('parts', []):
            if isinstance(part, str):
                text += part
            elif isinstance(part, dict) and 'text' in part:
                text += part['text']
    elif isinstance(content, str):
        text = content
    elif isinstance(content, dict) and 'text' in content:
        text = content['text']

    return text, content_type


def count_siblings(nodes: Dict[str, Dict[str, Any]], node_id: str) -> int:
    """Count sibling nodes."""
    node = nodes.get(node_id)
    if not node:
        return 0

    parent_id = node.get('parent_id')
    if not parent_id or parent_id not in nodes:
        return 0

    return len([
        child_id for child_id in nodes[parent_id].get('children_ids', [])
        if child_id != node_id
    ])


def is_regeneration(nodes: Dict[str, Dict[str, Any]], node_id: str) -> bool:
    """Check if node is a regenerated response."""
    node = nodes.get(node_id)
    if not node or node.get('is_user'):
        return False

    parent_id = node.get('parent_id')
    if not parent_id or parent_id not in nodes:
        return False

    parent = nodes[parent_id]
    if not parent.get('is_user'):
        return False

    # Multiple assistant children of same prompt indicates regeneration
    assistant_siblings = [
        child_id for child_id in parent.get('children_ids', [])
        if child_id in nodes and not nodes[child_id].get('is_user')
    ]

    return len(assistant_siblings) > 1


def find_replaced_node(nodes: Dict[str, Dict[str, Any]], node_id: str) -> Optional[str]:
    """Find replaced node ID for edited prompts."""
    # Placeholder for edit detection logic
    return None


def compute_turn_number(nodes: Dict[str, Dict[str, Any]], node_id: str) -> int:
    """Compute 1-based turn number."""
    path = compute_path_from_root(nodes, node_id)
    return len(path)


def determine_generation_type(nodes: Dict[str, Dict[str, Any]], node_id: str) -> str:
    """Classify node generation type."""
    node = nodes.get(node_id, {})

    if node.get('is_user'):
        if not node.get('parent_id'):
            return 'initial_prompt'
        return 'user_continuation'
    else:
        if is_regeneration(nodes, node_id):
            return 'regeneration'
        return 'standard_response'
