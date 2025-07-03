"""
CartaEmbedder: Semantic embedding generation.

CartaEmbedder class retrieves and returns high-dimensional 
vector embeddings from OpenAI for the parsed conversation trees.
"""

from .embedder import CartaEmbedder

__all__ = ["CartaEmbedder"]