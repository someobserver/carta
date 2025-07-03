"""
CartaEmbedder: Semantic embedding generation.

Retrieves and returns high-dimensional vector embeddings from OpenAI
for the parsed conversation trees.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from .openai_utils import OpenAIEmbedder

logger = logging.getLogger(__name__)


class CartaEmbedder:
    """Generates and manages embeddings for parsed conversation trees."""

    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-large"):
        """Initialize the embedder.

        Args:
            api_key: OpenAI API key. If None, will try to use OPENAI_API_KEY environment variable.
            model: The embedding model to use. Default is text-embedding-3-large.
        """
        self.openai_embedder = OpenAIEmbedder(api_key=api_key, model=model)
        logger.info(f"Initialized Carta Embedder with model: {model}")

    def process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Process a parsed conversation file and generate embeddings.

        Args:
            file_path: Path to the parsed JSON file.

        Returns:
            List of conversation data enriched with embeddings.
        """
        if not file_path:
            logger.error("No file path provided")
            return []

        file_path = Path(file_path)
        logger.info(f"Processing file: {file_path}")

        # Load the parsed data
        try:
            with open(file_path, 'r') as f:
                conversations = json.load(f)
            logger.info(f"Loaded {len(conversations)} conversations from {file_path}")
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return []
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in file: {file_path}")
            return []
        except Exception as e:
            logger.error(f"Error loading file: {e}")
            return []

        # Process each conversation
        enriched_conversations = []
        for convo_idx, conversation in enumerate(conversations):
            logger.info(f"Processing conversation {convo_idx+1}/{len(conversations)}")
            enriched_conversation = self.process_conversation(conversation)
            enriched_conversations.append(enriched_conversation)

        logger.info(f"Completed processing {len(conversations)} conversations")
        return enriched_conversations

    def process_conversation(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single conversation, generating embeddings for nodes and pairs.

        Args:
            conversation: Parsed conversation data.

        Returns:
            Conversation data enriched with embeddings.
        """
        # Create a copy to avoid modifying the original
        conversation = conversation.copy()

        # Process nodes
        if 'nodes' in conversation:
            logger.info(f"Processing {len(conversation['nodes'])} nodes")
            self._process_nodes(conversation['nodes'])

        # Process pairs
        if 'pairs' in conversation:
            logger.info(f"Processing {len(conversation['pairs'])} pairs")
            self._process_pairs(conversation)

        # Calculate additional semantic metrics
        if 'nodes' in conversation:
            logger.info("Calculating semantic ancestry metrics")
            self._calculate_semantic_ancestry(conversation)

        return conversation

    def _process_nodes(self, nodes: Dict[str, Dict[str, Any]]) -> None:
        """Generate embeddings for all nodes in a conversation.

        Args:
            nodes: Dictionary of nodes from the conversation.
        """
        # Extract text content from nodes for batch processing
        node_texts = {}
        for node_id, node in nodes.items():
            text = self._extract_node_text(node)
            if text:
                node_texts[node_id] = text

        # Generate embeddings in batches for efficiency
        logger.info(f"Generating embeddings for {len(node_texts)} nodes")
        node_ids = list(node_texts.keys())
        texts = [node_texts[node_id] for node_id in node_ids]

        embeddings = self.openai_embedder.get_embeddings_batch(texts)

        # Attach embeddings back to corresponding nodes
        for idx, node_id in enumerate(node_ids):
            nodes[node_id]['embedding'] = embeddings[idx]

    def _extract_node_text(self, node: Dict[str, Any]) -> Optional[str]:
        """Extract the text content from a node.

        Args:
            node: Node data.

        Returns:
            Extracted text or None if no valid text found.
        """
        if not node or 'message' not in node:
            return None

        message = node.get('message', {})

        # Handle different ChatGPT message content structures
        if 'content' in message:
            content = message['content']

            # Handle simple text content
            if isinstance(content, dict) and 'text' in content:
                return content['text']

            # Handle multimodal content (text + images/files)
            if isinstance(content, dict) and 'parts' in content:
                parts = content.get('parts', [])
                texts = []
                for part in parts:
                    if isinstance(part, dict) and 'text' in part:
                        texts.append(part['text'])
                return " ".join(texts) if texts else None

        return None

    def _process_pairs(self, conversation: Dict[str, Any]) -> None:
        """Generate embeddings for all prompt-response pairs in a conversation.

        Args:
            conversation: Conversation data containing nodes and pairs.
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
                prompt_text = self._extract_node_text(nodes[prompt_id])
                response_text = self._extract_node_text(nodes[response_id])

                if prompt_text and response_text:
                    formatted_text = self.openai_embedder.format_pair_for_embedding(prompt_text, response_text)
                    pair_texts.append(formatted_text)
                    valid_pairs.append(pair)
                else:
                    pair_texts.append("")
                    valid_pairs.append(pair)

        # Generate embeddings for valid pairs
        if valid_pairs:
            logger.info(f"Generating embeddings for {len(valid_pairs)} pairs")
            embeddings = self.openai_embedder.get_embeddings_batch(pair_texts)

            # Add embeddings back to pairs
            for idx, pair in enumerate(valid_pairs):
                pair['embedding'] = embeddings[idx]

    def _calculate_semantic_ancestry(self, conversation: Dict[str, Any]) -> None:
        """Calculate semantic ancestry metrics for the conversation.

        Args:
            conversation: Conversation data with nodes and their embeddings.
        """
        nodes = conversation.get('nodes', {})

        # Calculate semantic distances between parent-child nodes
        for node_id, node in nodes.items():
            parent_id = node.get('parent_id')
            if parent_id and parent_id in nodes:
                parent_embedding = nodes[parent_id].get('embedding')
                node_embedding = node.get('embedding')

                if parent_embedding and node_embedding:
                    distance = self.openai_embedder.calculate_cosine_distance(
                        parent_embedding, node_embedding
                    )

                    # Add to derived properties
                    if 'derived' not in node:
                        node['derived'] = {}

                    node['derived']['semantic_distance_from_parent'] = distance

        # Calculate semantic distances between siblings
        for node_id, node in nodes.items():
            parent_id = node.get('parent_id')
            if parent_id and parent_id in nodes:
                siblings = [
                    sib_id for sib_id, sib in nodes.items()
                    if sib.get('parent_id') == parent_id and sib_id != node_id
                ]

                if siblings and 'embedding' in node:
                    # Calculate average distance to siblings
                    sibling_distances = []
                    for sib_id in siblings:
                        if 'embedding' in nodes[sib_id]:
                            distance = self.openai_embedder.calculate_cosine_distance(
                                node['embedding'], nodes[sib_id]['embedding']
                            )
                            sibling_distances.append(distance)

                    if sibling_distances:
                        avg_sibling_distance = sum(sibling_distances) / len(sibling_distances)

                        # Add to derived properties
                        if 'derived' not in node:
                            node['derived'] = {}

                        node['derived']['avg_sibling_semantic_distance'] = avg_sibling_distance

        # Calculate semantic distance from mainline for branch nodes
        mainline_nodes = {
            node_id: node for node_id, node in nodes.items()
            if node.get('derived', {}).get('is_mainline', False)
        }

        branch_nodes = {
            node_id: node for node_id, node in nodes.items()
            if not node.get('derived', {}).get('is_mainline', False)
        }

        for branch_id, branch_node in branch_nodes.items():
            # Find the mainline node at the same turn number if possible
            turn_number = branch_node.get('derived', {}).get('turn_number')
            mainline_at_turn = None

            if turn_number is not None:
                mainline_at_turn = next(
                    (node for node_id, node in mainline_nodes.items()
                     if node.get('derived', {}).get('turn_number') == turn_number),
                    None
                )

            # Calculate distance if we found a matching mainline node
            if mainline_at_turn and 'embedding' in branch_node and 'embedding' in mainline_at_turn:
                distance = self.openai_embedder.calculate_cosine_distance(
                    branch_node['embedding'], mainline_at_turn['embedding']
                )

                # Add to derived properties
                if 'derived' not in branch_node:
                    branch_node['derived'] = {}

                branch_node['derived']['mainline_semantic_distance'] = distance

    def save_to_json(self, data: List[Dict[str, Any]], output_filename: str) -> str:
        """Save the enriched conversation data to a JSON file.

        Args:
            data: List of enriched conversation data.
            output_filename: Filename for the output file.

        Returns:
            Path to the saved file.
        """
        if not data:
            logger.warning("No data to save")
            return ""

        # Convert string path to Path object
        output_path = Path(output_filename)

        try:
            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved enriched data to {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            return ""
