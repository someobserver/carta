"""
ChatGPT conversation parsing library.

Parser for reconstructing ChatGPT conversation trees from JSON exports.
Maintains full branch structure and derived semantic metadata.
"""

from .parser import CartaParser

__all__ = ["CartaParser"]
