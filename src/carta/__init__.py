"""
CARTA - Conversation Archive for Recursive Thought Analysis.

A Python library for processing and analyzing ChatGPT conversation exports
using semantic embeddings and recursive tree structures.
"""

__version__ = "0.1.0"
__author__ = "Inside The Black Box LLC"

from .parser.parser import CartaParser
from .embedder.embedder import CartaEmbedder

__all__ = ["CartaParser", "CartaEmbedder"]
