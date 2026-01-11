"""
Passepartout - Knowledge Base & Context Module

Named after Passepartout from "Around the World in 80 Days" - the resourceful
and knowledgeable companion who provides context and assists with navigation.

This module implements:
- Semantic embeddings for text
- Vector storage for efficient similarity search
- Note management with Markdown and Git
- Context retrieval for cognitive reasoning
- Note review with SM-2 spaced repetition
- Intelligent note enrichment
- Cross-source search (email, calendar, teams, files, web)

Usage:
    from src.passepartout import EmbeddingGenerator, VectorStore, NoteManager, ContextEngine
    from src.passepartout import NoteScheduler, NoteReviewer, BackgroundWorker
    from src.passepartout import CrossSourceEngine, CrossSourceConfig
"""

from src.passepartout.background_worker import (
    BackgroundWorker,
    BackgroundWorkerManager,
    WorkerConfig,
    WorkerState,
    WorkerStats,
)
from src.passepartout.context_engine import ContextEngine, ContextRetrievalResult
from src.passepartout.embeddings import EmbeddingGenerator
from src.passepartout.enricher import (
    EnricherError,
    PKMEnricher,
    create_enricher,
)
from src.passepartout.note_enricher import (
    Enrichment,
    EnrichmentContext,
    EnrichmentPipeline,
    EnrichmentResult,
    EnrichmentSource,
    NoteEnricher,
)
from src.passepartout.note_manager import Note, NoteManager
from src.passepartout.note_merger import (
    Change,
    Conflict,
    ConflictType,
    MergeResult,
    MergeStrategy,
    NoteMerger,
)
from src.passepartout.note_metadata import (
    EnrichmentRecord,
    NoteMetadata,
    NoteMetadataStore,
)
from src.passepartout.note_reviewer import (
    ActionType,
    NoteReviewer,
    ReviewAction,
    ReviewAnalysis,
    ReviewContext,
    ReviewResult,
)
from src.passepartout.note_scheduler import (
    NoteScheduler,
    SchedulingResult,
    create_scheduler,
)

# Note review system
from src.passepartout.note_types import (
    ImportanceLevel,
    NoteType,
    ReviewConfig,
    get_review_config,
)
from src.passepartout.vector_store import VectorStore

__all__ = [
    # Original exports
    "EmbeddingGenerator",
    "VectorStore",
    "NoteManager",
    "Note",
    "ContextEngine",
    "ContextRetrievalResult",
    # Note types
    "NoteType",
    "ImportanceLevel",
    "ReviewConfig",
    "get_review_config",
    # Metadata
    "NoteMetadata",
    "NoteMetadataStore",
    "EnrichmentRecord",
    # Scheduler
    "NoteScheduler",
    "SchedulingResult",
    "create_scheduler",
    # Reviewer
    "NoteReviewer",
    "ReviewAction",
    "ReviewAnalysis",
    "ReviewContext",
    "ReviewResult",
    "ActionType",
    # Enricher (v2.1 PKM)
    "PKMEnricher",
    "EnricherError",
    "create_enricher",
    # Enricher (original)
    "NoteEnricher",
    "Enrichment",
    "EnrichmentContext",
    "EnrichmentResult",
    "EnrichmentSource",
    "EnrichmentPipeline",
    # Merger
    "NoteMerger",
    "MergeResult",
    "MergeStrategy",
    "Change",
    "Conflict",
    "ConflictType",
    # Background worker
    "BackgroundWorker",
    "BackgroundWorkerManager",
    "WorkerConfig",
    "WorkerState",
    "WorkerStats",
]

__version__ = "1.1.0"
