"""
Pair Embedder

Functions for generating embeddings for prompt-response pairs.
"""

import logging
from typing import Dict, List, Any

from .node_embedder import extract_node_text

logger = logging.getLogger(__name__)


def process_pairs(conversation: Dict[str, Any], embedder) -> None:
    """Generate embeddings for all prompt-response pairs in a conversation.

    Args:
        conversation: Conversation data containing nodes and pairs.
        embedder: The OpenAI embedder instance for generating embeddings.
    """
    pairs = conversation.get('pairs', [])
    nodes = conversation.get('nodes', {})

    # Extract texts for all pairs
    pair_texts = []
    valid_pairs = []

    for pair in pairs:
        prompt_id = pair.get('prompt_id')
        response_id = pair.get('response_id')

        if prompt_id and response_id and prompt_id in nodes and response_id in nodes:
            prompt_text = extract_node_text(nodes[prompt_id])
            response_text = extract_node_text(nodes[response_id])

            if prompt_text and response_text:
                formatted_text = embedder.format_pair_for_embedding(prompt_text, response_text)
                pair_texts.append(formatted_text)
                valid_pairs.append(pair)
            else:
                pair_texts.append("")
                valid_pairs.append(pair)

    # Generate embeddings for valid pairs
    if valid_pairs:
        logger.info(f"Generating embeddings for {len(valid_pairs)} pairs")
        embeddings = embedder.get_embeddings_batch(pair_texts)

        # Add embeddings back to pairs
        for idx, pair in enumerate(valid_pairs):
            pair['embedding'] = embeddings[idx]
