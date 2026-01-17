import time
import asyncio
from pathlib import Path
import logging
import sys
import shutil

# Add src to path
sys.path.append(".")

import sys
from unittest.mock import MagicMock

# Mock heavy dependencies BEFORE imports
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["chromadb"] = MagicMock()
sys.modules["git"] = MagicMock()
sys.modules["git.repo"] = MagicMock()
sys.modules["git.exc"] = MagicMock()
sys.modules["src.passepartout.embeddings"] = MagicMock()
sys.modules["src.passepartout.vector_store"] = MagicMock()

# Mock specific classes that are instantiated
mock_vec_store = MagicMock()
sys.modules["src.passepartout.vector_store"].VectorStore.return_value = mock_vec_store

from src.passepartout.note_manager import NoteManager
# from src.monitoring.logger import setup_logging  # startup logging not needed

# Setup partial logging to avoid noise
logging.basicConfig(level=logging.INFO)


def create_dummy_notes(n=100):
    """Create N dummy notes for testing"""
    base_dir = Path("./temp_notes_benchmark")
    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True)

    print(f"Creating {n} dummy notes...")
    for i in range(n):
        content = f"""---
title: Note {i}
type: note
tags: [benchmark, test]
created: 2024-01-01T10:00:00
modified: 2024-01-01T10:00:00
---

# Note {i}

This is a benchmark note number {i}.
It has some content to simulate real file reading.
Lorem ipsum dolor sit amet.
"""
        (base_dir / f"note_{i}.md").write_text(content)

    return base_dir


def benchmark_load(n=100):
    notes_dir = create_dummy_notes(n)

    print("Initializing NoteManager...")
    manager = NoteManager(notes_dir, cache_max_size=n * 2)

    print("Starting Cold Load benchmark...")
    start = time.time()
    notes = manager.get_all_notes()
    end = time.time()

    print(f"Loaded {len(notes)} notes in {end - start:.4f} seconds")
    print(f"Average: {(end - start) / n * 1000:.2f} ms/note")

    # Clean up
    shutil.rmtree(notes_dir)


if __name__ == "__main__":
    benchmark_load(500)
