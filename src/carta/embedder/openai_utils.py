"""
Utilities for interacting with the OpenAI API for generating embeddings.

This module provides clean abstractions for embedding generation and semantic
distance calculations, supporting the field-theoretic analysis of conversation trees.
"""

import os
import logging
import time
from typing import List, Optional
import numpy as np
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIEmbedder:
    """Utility class for generating embeddings using OpenAI's API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-large"):
        """Initialize the OpenAI embedder.

        Args:
            api_key: OpenAI API key. If None, will try to use OPENAI_API_KEY environment variable.
            model: The embedding model to use. Default is text-embedding-3-large.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "No OpenAI API key provided. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        self.dimension = 2000 if model == "text-embedding-3-large" else 1536

        logger.info(f"Initialized OpenAI embedder with model: {model}")

    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: The text to embed.

        Returns:
            List of embedding values.
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding. Returning zero vector.")
            return [0.0] * self.dimension

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            embedding = response.data[0].embedding
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def get_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Generate embeddings for a batch of texts efficiently.

        Args:
            texts: List of texts to embed.
            batch_size: Maximum number of texts to process in a single API call.

        Returns:
            List of embeddings (each is a list of float values).
        """
        if not texts:
            logger.warning("Empty list provided for batch embedding.")
            return []

        # Filter out empty texts
        valid_texts = [text for text in texts if text and text.strip()]
        empty_indices = [i for i, text in enumerate(texts) if not text or not text.strip()]

        all_embeddings = []
        for i in range(0, len(valid_texts), batch_size):
            batch = valid_texts[i:i+batch_size]

            try:
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(valid_texts) + batch_size - 1)//batch_size}")
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )

                # Sort by index as the API might not return in the same order
                batch_embeddings = [data.embedding for data in sorted(response.data, key=lambda x: x.index)]
                all_embeddings.extend(batch_embeddings)

                # Rate limiting: sleep to avoid hitting API limits
                if i + batch_size < len(valid_texts):
                    time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error in batch {i//batch_size + 1}: {e}")
                # Insert zero vectors for this batch as fallback
                zero_vectors = [[0.0] * self.dimension for _ in range(len(batch))]
                all_embeddings.extend(zero_vectors)

        # Reinsert zero vectors for empty texts
        result = []
        valid_idx = 0
        for i in range(len(texts)):
            if i in empty_indices:
                result.append([0.0] * self.dimension)
            else:
                result.append(all_embeddings[valid_idx])
                valid_idx += 1

        return result

    def format_pair_for_embedding(self, prompt_text: str, response_text: str) -> str:
        """Format a prompt-response pair for embedding with clear semantic boundaries.

        Args:
            prompt_text: The prompt/question text.
            response_text: The response/answer text.

        Returns:
            Formatted text with semantic boundaries.
        """
        formatted_text = f"|Prompt from user:\n---\n{prompt_text}\n\n|Response from assistant:\n---\n{response_text}"
        return formatted_text

    def calculate_cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector.
            embedding2: Second embedding vector.

        Returns:
            Cosine similarity score between 0 and 1.
        """
        if not embedding1 or not embedding2:
            return 0.0

        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Calculate cosine similarity
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        return float(similarity)

    def calculate_cosine_distance(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine distance between two embeddings (1 - similarity).

        Args:
            embedding1: First embedding vector.
            embedding2: Second embedding vector.

        Returns:
            Cosine distance score between 0 and 2.
        """
        similarity = self.calculate_cosine_similarity(embedding1, embedding2)
        return 1.0 - similarity
