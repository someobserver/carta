"""
CartaParser: ChatGPT conversation tree parsing operations.

Extracts conversation architectures from ChatGPT JSON exports.
Preserves branches + alternates + derived semantic parameters.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .node_processor import process_nodes, extract_node_data
from .path_analyzer import find_root_nodes, find_current_node, determine_mainline_path
from .pair_creator import create_pairs

logger = logging.getLogger(__name__)


class CartaParser:
    """Parses ChatGPT JSON exports preserving full conversation tree structure."""

    def __init__(self, output_dir: Optional[str] = None):
        """Initialize parser with output directory."""
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def parse_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Parse ChatGPT JSON export file."""
        logger.info(f"Parsing file: {filepath}")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading JSON file: {e}")
            return []

        # Handle both single conversation and array formats from ChatGPT exports
        if isinstance(data, list):
            conversations = data
        else:
            conversations = [data]

        results = []
        for conversation_data in conversations:
            parsed_conversation = self._parse_conversation(conversation_data)
            if parsed_conversation:
                results.append(parsed_conversation)

        return results

    def _parse_conversation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse single conversation data."""
        conversation = self._extract_conversation_metadata(data)

        mapping = data.get('mapping', {})
        if not mapping:
            logger.error("No mapping found in JSON file")
            return {}

        root_nodes = self._find_root_nodes(mapping)
        if not root_nodes:
            logger.error("No root nodes found in the conversation tree")
            return {}

        conversation['root_id'] = root_nodes[0] if root_nodes else None

        current_node_id = self._find_current_node(data, mapping)
        conversation['current_node'] = current_node_id

        nodes = self._process_nodes(mapping, current_node_id)
        pairs = self._create_pairs(nodes)

        return {
            'conversation': conversation,
            'nodes': nodes,
            'pairs': pairs
        }

    def _extract_conversation_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract conversation-level metadata."""
        return {
            'id': data.get('id'),
            'title': data.get('title', 'Untitled Conversation'),
            'create_time': data.get('create_time'),
            'update_time': data.get('update_time'),
            'default_model_slug': data.get('model', {}).get('slug') if data.get('model') else None
        }

    def _find_root_nodes(self, mapping: Dict[str, Any]) -> List[str]:
        """Find root nodes in conversation tree."""
        return find_root_nodes(mapping)

    def _find_current_node(self, data: Dict[str, Any], mapping: Dict[str, Any]) -> Optional[str]:
        """Find current node ID (mainline endpoint)."""
        return find_current_node(data, mapping)

    def _process_nodes(self, mapping: Dict[str, Any], current_node_id: Optional[str]) -> Dict[str, Dict[str, Any]]:
        """Process all nodes with derived parameters."""
        return process_nodes(mapping, current_node_id)

    def _extract_node_data(self, node_id: str, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract core node data from JSON."""
        return extract_node_data(node_id, node_data)

    def _determine_mainline_path(self, nodes: Dict[str, Dict[str, Any]], current_node_id: Optional[str]) -> List[str]:
        """Determine mainline path from root to current node."""
        return determine_mainline_path(nodes, current_node_id)

    def _compute_path_from_root(self, nodes: Dict[str, Dict[str, Any]], node_id: str) -> List[str]:
        """Compute path from root to given node."""
        path = []
        current = node_id

        if node_id not in nodes:
            return path

        # Walk backwards to root
        while current:
            path.insert(0, current)
            current = nodes[current]['parent_id']

        return path

    def _count_siblings(self, nodes: Dict[str, Dict[str, Any]], node_id: str) -> int:
        """Count sibling nodes."""
        if node_id not in nodes:
            return 0

        parent_id = nodes[node_id]['parent_id']
        if not parent_id or parent_id not in nodes:
            return 0

        return len(nodes[parent_id]['children_ids'])

    def _is_regeneration(self, nodes: Dict[str, Dict[str, Any]], node_id: str) -> bool:
        """Determine if node is a regeneration (second+ child of user message)."""
        if node_id not in nodes:
            return False

        parent_id = nodes[node_id]['parent_id']
        if not parent_id or parent_id not in nodes:
            return False

        parent_role = nodes[parent_id]['message']['author'].get('role')
        node_role = nodes[node_id]['message']['author'].get('role')

        # Assistant following assistant suggests regeneration
        if parent_role == 'assistant' and node_role == 'assistant':
            return True

        # Not first assistant response to user message
        if parent_role == 'user' and node_role == 'assistant':
            children = nodes[parent_id]['children_ids']
            if children and children[0] != node_id:
                return True

        return False

    def _find_divergence_point(self, path: List[str], mainline_path: List[str]) -> Optional[str]:
        """Find where path diverges from mainline."""
        if not path or not mainline_path:
            return None

        common_prefix_length = 0
        max_length = min(len(path), len(mainline_path))

        for i in range(max_length):
            if path[i] == mainline_path[i]:
                common_prefix_length = i + 1
            else:
                break

        if common_prefix_length == 0:
            return None

        return path[common_prefix_length - 1]

    def _find_replaced_node(self, nodes: Dict[str, Dict[str, Any]], node_id: str) -> Optional[str]:
        """Find node this replaces (edited prompts). Placeholder implementation."""
        # Requires metadata indicating edits/replacements
        return None

    def _compute_turn_number(self, nodes: Dict[str, Dict[str, Any]], node_id: str) -> int:
        """Compute turn number for node."""
        if node_id not in nodes:
            return 0

        path = self._compute_path_from_root(nodes, node_id)
        return len(path)

    def _determine_generation_type(self, nodes: Dict[str, Dict[str, Any]], node_id: str) -> str:
        """Determine generation type: primary, regeneration, alternative, or edited."""
        if node_id not in nodes:
            return "unknown"

        node = nodes[node_id]

        if not node['parent_id']:
            return "primary"

        if node['derived']['is_regeneration']:
            return "regeneration"

        if node['derived']['replaced_node_id']:
            return "edited"

        if not node['derived']['is_mainline']:
            return "alternative"

        return "primary"

    def _create_pairs(self, nodes: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create prompt-response pairs from nodes."""
        return create_pairs(nodes)

    def save_to_json(self, parsed_data: List[Dict[str, Any]], output_filename: Optional[str] = None) -> str:
        """Save parsed data to JSON file."""
        if not parsed_data:
            logger.warning("No parsed data to save")
            return ""

        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if 'conversation' in parsed_data[0]:
                conversation_id = parsed_data[0]['conversation'].get('id', 'unknown')
            else:
                conversation_id = 'unknown'
            output_filename = f"parsed_{timestamp}_{conversation_id}.json"

        output_path = Path(output_filename)
        if not output_path.is_absolute():
            output_path = self.output_dir / output_path.name

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, indent=2)
            logger.info(f"Saved parsed data to {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Error saving parsed data: {e}")
            return ""
