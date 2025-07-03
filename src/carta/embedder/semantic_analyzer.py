"""Semantic relationship analysis for embedded conversation nodes."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def calculate_semantic_ancestry(conversation: Dict[str, Any], embedder) -> None:
    """Calculate semantic distance metrics for conversation nodes."""
    nodes = conversation.get('nodes', {})

    calculate_parent_child_distances(nodes, embedder)
    calculate_sibling_distances(nodes, embedder)
    calculate_branch_mainline_distances(nodes, embedder)


def calculate_parent_child_distances(nodes: Dict[str, Dict[str, Any]], embedder) -> None:
    """Calculate cosine distances between parent-child node pairs."""
    for node_id, node in nodes.items():
        parent_id = node.get('parent_id')
        if parent_id and parent_id in nodes:
            parent_embedding = nodes[parent_id].get('embedding')
            node_embedding = node.get('embedding')

            if parent_embedding and node_embedding:
                distance = embedder.calculate_cosine_distance(
                    parent_embedding, node_embedding
                )

                if 'derived' not in node:
                    node['derived'] = {}

                node['derived']['semantic_distance_from_parent'] = distance


def calculate_sibling_distances(nodes: Dict[str, Dict[str, Any]], embedder) -> None:
    """Calculate average cosine distances between sibling nodes."""
    for node_id, node in nodes.items():
        parent_id = node.get('parent_id')
        if parent_id and parent_id in nodes:
            siblings = [
                sib_id for sib_id, sib in nodes.items()
                if sib.get('parent_id') == parent_id and sib_id != node_id
            ]

            if siblings and 'embedding' in node:
                sibling_distances = []
                for sib_id in siblings:
                    if 'embedding' in nodes[sib_id]:
                        distance = embedder.calculate_cosine_distance(
                            node['embedding'], nodes[sib_id]['embedding']
                        )
                        sibling_distances.append(distance)

                if sibling_distances:
                    avg_sibling_distance = sum(sibling_distances) / len(sibling_distances)

                    if 'derived' not in node:
                        node['derived'] = {}

                    node['derived']['avg_sibling_semantic_distance'] = avg_sibling_distance


def calculate_branch_mainline_distances(nodes: Dict[str, Dict[str, Any]], embedder) -> None:
    """Calculate semantic distance from branch nodes to mainline divergence points."""
    mainline_nodes = {
        node_id: node for node_id, node in nodes.items()
        if node.get('derived', {}).get('is_mainline', False)
    }

    branch_nodes = {
        node_id: node for node_id, node in nodes.items()
        if not node.get('derived', {}).get('is_mainline', False)
    }

    for node_id, node in branch_nodes.items():
        divergence_point = node.get('derived', {}).get('mainline_divergence_point')

        if divergence_point and divergence_point in mainline_nodes:
            branch_embedding = node.get('embedding')
            mainline_embedding = mainline_nodes[divergence_point].get('embedding')

            if branch_embedding and mainline_embedding:
                distance = embedder.calculate_cosine_distance(
                    branch_embedding, mainline_embedding
                )

                if 'derived' not in node:
                    node['derived'] = {}

                node['derived']['semantic_distance_from_mainline'] = distance
