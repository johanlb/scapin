"""
Passepartout - Knowledge Base & Context Module

Named after Passepartout from "Around the World in 80 Days" - the resourceful
and knowledgeable companion who provides context and assists with navigation.

This module implements:
- Semantic embeddings for text
- Vector storage for efficient similarity search
- Note management with Markdown and Git
- Context retrieval for cognitive reasoning

Usage:
    from src.passepartout import EmbeddingGenerator, VectorStore, NoteManager, ContextEngine
"""

from src.passepartout.context_engine import ContextEngine, ContextRetrievalResult
from src.passepartout.embeddings import EmbeddingGenerator
from src.passepartout.note_manager import Note, NoteManager
from src.passepartout.vector_store import VectorStore

__all__ = [
    "EmbeddingGenerator",
    "VectorStore",
    "NoteManager",
    "Note",
    "ContextEngine",
    "ContextRetrievalResult",
]

__version__ = "1.0.0"
