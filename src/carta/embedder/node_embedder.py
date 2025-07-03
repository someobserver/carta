"""
Node Embedder

Functions for generating embeddings for conversation nodes.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def process_nodes(nodes: Dict[str, Dict[str, Any]], embedder) -> None:
    """Generate embeddings for all nodes in a conversation.

    Args:
        nodes: Dictionary of nodes from the conversation.
        embedder: The OpenAI embedder instance for generating embeddings.
    """
    # Extract texts from nodes for batch processing
    node_texts = {}
    for node_id, node in nodes.items():
        text = extract_node_text(node)
        if text:
            node_texts[node_id] = text

    # Generate embeddings in batches
    logger.info(f"Generating embeddings for {len(node_texts)} nodes")
    node_ids = list(node_texts.keys())
    texts = [node_texts[node_id] for node_id in node_ids]

    embeddings = embedder.get_embeddings_batch(texts)

    # Add embeddings back to nodes
    for idx, node_id in enumerate(node_ids):
        nodes[node_id]['embedding'] = embeddings[idx]


def extract_node_text(node: Dict[str, Any]) -> Optional[str]:
    """Extract the text content from a node.

    Args:
        node: Node data.

    Returns:
        Extracted text or None if no valid text found.
    """
    if not node or 'message' not in node:
        return None

    # If the node already has extracted text, use that
    if 'text' in node and node['text']:
        return node['text']

    message = node.get('message', {})

    # Handle different content structures
    if 'content' in message:
        content = message['content']

        # Handle text content
        if isinstance(content, dict) and 'text' in content:
            return content['text']

        # Handle multimodal content
        if isinstance(content, dict) and 'parts' in content:
            parts = content.get('parts', [])
            texts = []
            for part in parts:
                if isinstance(part, str):
                    texts.append(part)
                elif isinstance(part, dict) and 'text' in part:
                    texts.append(part['text'])
            return " ".join(texts) if texts else None

    return None
