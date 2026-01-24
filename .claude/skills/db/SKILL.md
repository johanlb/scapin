---
name: db
description: Base de données Scapin - SQLite, schéma, requêtes, migrations, FAISS. Utiliser pour comprendre ou modifier la persistance des données.
allowed-tools: Bash, Read, Grep, Glob
---

# Base de Données Scapin

Guide pour la persistance des données : SQLite et FAISS.

---

## Architecture de Stockage

```
data/
├── scapin.db              # SQLite - données structurées
├── faiss/
│   ├── notes.index        # Index vectoriel notes
│   └── notes_ids.json     # Mapping ID → vecteur
├── logs/                  # Logs JSON (non-DB)
└── errors.db              # SQLite - erreurs persistées
```

| Stockage | Usage | Technologie |
|----------|-------|-------------|
| **Données structurées** | Notes, emails, config | SQLite |
| **Recherche sémantique** | Embeddings notes | FAISS |
| **Logs** | Historique traitement | JSON files |
| **Erreurs** | Erreurs persistées | SQLite |

---

## SQLite - Schéma Principal

### Tables Principales

```sql
-- Notes PKM
CREATE TABLE notes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    folder_path TEXT,
    note_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quality_score INTEGER,
    apple_notes_id TEXT UNIQUE,
    metadata JSON
);

-- Index pour recherche
CREATE INDEX idx_notes_folder ON notes(folder_path);
CREATE INDEX idx_notes_updated ON notes(updated_at DESC);
CREATE INDEX idx_notes_type ON notes(note_type);
CREATE INDEX idx_notes_apple_id ON notes(apple_notes_id);

-- Queue de traitement
CREATE TABLE queue_items (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,  -- 'email', 'teams', 'calendar'
    source_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    analysis JSON,
    metadata JSON,
    UNIQUE(source_type, source_id)
);

CREATE INDEX idx_queue_status ON queue_items(status);
CREATE INDEX idx_queue_priority ON queue_items(priority DESC, created_at ASC);

-- Feedback utilisateur
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    ai_suggestion TEXT,
    was_correct BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);
```

### Schéma Erreurs

```sql
-- data/errors.db
CREATE TABLE errors (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,      -- 'IMAP', 'AI', 'DATABASE', etc.
    severity TEXT NOT NULL,      -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    message TEXT NOT NULL,
    details JSON,
    traceback TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE INDEX idx_errors_category ON errors(category);
CREATE INDEX idx_errors_severity ON errors(severity);
CREATE INDEX idx_errors_resolved ON errors(resolved);
```

---

## Requêtes Courantes

### Notes

```python
# Récupérer une note par ID
async def get_note(db: Database, note_id: str) -> Note | None:
    row = await db.fetchone(
        "SELECT * FROM notes WHERE id = ?",
        (note_id,)
    )
    return Note(**row) if row else None

# Notes par dossier
async def get_notes_by_folder(db: Database, folder: str) -> list[Note]:
    rows = await db.fetchall(
        """SELECT * FROM notes
           WHERE folder_path = ? OR folder_path LIKE ?
           ORDER BY updated_at DESC""",
        (folder, f"{folder}/%")
    )
    return [Note(**row) for row in rows]

# Recherche full-text
async def search_notes(db: Database, query: str, limit: int = 20) -> list[Note]:
    rows = await db.fetchall(
        """SELECT * FROM notes
           WHERE title LIKE ? OR content LIKE ?
           ORDER BY updated_at DESC
           LIMIT ?""",
        (f"%{query}%", f"%{query}%", limit)
    )
    return [Note(**row) for row in rows]
```

### Queue

```python
# Prochain item à traiter
async def get_next_queue_item(db: Database) -> QueueItem | None:
    row = await db.fetchone(
        """SELECT * FROM queue_items
           WHERE status = 'pending'
           ORDER BY priority DESC, created_at ASC
           LIMIT 1"""
    )
    return QueueItem(**row) if row else None

# Stats de la queue
async def get_queue_stats(db: Database) -> dict:
    rows = await db.fetchall(
        """SELECT status, COUNT(*) as count
           FROM queue_items
           GROUP BY status"""
    )
    return {row["status"]: row["count"] for row in rows}
```

---

## Patterns d'Accès

### Connection Context Manager

```python
import aiosqlite
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db():
    """Context manager pour connexion DB."""
    db = await aiosqlite.connect("data/scapin.db")
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()

# Usage
async def example():
    async with get_db() as db:
        await db.execute("INSERT INTO notes ...")
        await db.commit()
```

### Transaction

```python
async def transfer_item(db: Database, item_id: str, new_folder: str):
    """Opération transactionnelle."""
    async with db.transaction():
        # Plusieurs opérations atomiques
        await db.execute(
            "UPDATE notes SET folder_path = ? WHERE id = ?",
            (new_folder, item_id)
        )
        await db.execute(
            "INSERT INTO audit_log (action, item_id) VALUES (?, ?)",
            ("move", item_id)
        )
        # Commit automatique à la sortie du context
        # Rollback automatique si exception
```

### Batch Insert

```python
async def insert_notes_batch(db: Database, notes: list[Note]):
    """Insert batch pour performance."""
    await db.executemany(
        """INSERT OR REPLACE INTO notes (id, title, content, folder_path, updated_at)
           VALUES (?, ?, ?, ?, ?)""",
        [(n.id, n.title, n.content, n.folder_path, n.updated_at) for n in notes]
    )
    await db.commit()
```

---

## FAISS - Index Vectoriel

### Structure

```python
import faiss
import numpy as np

# Charger l'index
index = faiss.read_index("data/faiss/notes.index")

# Dimension des vecteurs (Claude embeddings)
EMBEDDING_DIM = 1024

# Nombre de vecteurs
print(f"Vectors: {index.ntotal}")
```

### Recherche Sémantique

```python
async def semantic_search(
    query_embedding: np.ndarray,
    k: int = 10
) -> list[tuple[str, float]]:
    """Recherche les k notes les plus similaires."""
    # query_embedding shape: (1, 1024)
    distances, indices = index.search(query_embedding, k)

    # Charger le mapping ID
    with open("data/faiss/notes_ids.json") as f:
        id_mapping = json.load(f)

    results = []
    for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
        if idx >= 0:  # -1 = pas de résultat
            note_id = id_mapping[str(idx)]
            similarity = 1 / (1 + dist)  # Convertir distance en similarité
            results.append((note_id, similarity))

    return results
```

### Mise à Jour de l'Index

```python
async def add_to_index(note_id: str, embedding: np.ndarray):
    """Ajouter un vecteur à l'index."""
    global index, id_mapping

    # Ajouter le vecteur
    new_idx = index.ntotal
    index.add(embedding.reshape(1, -1))

    # Mettre à jour le mapping
    id_mapping[str(new_idx)] = note_id

    # Sauvegarder
    faiss.write_index(index, "data/faiss/notes.index")
    with open("data/faiss/notes_ids.json", "w") as f:
        json.dump(id_mapping, f)

async def rebuild_index():
    """Reconstruire l'index complet."""
    # Appeler via API: POST /api/notes/reindex
    pass
```

---

## Migrations

### Structure des Migrations

```
src/core/migrations/
├── __init__.py
├── migration_001_initial.py
├── migration_002_add_quality_score.py
└── migration_003_add_briefing_status.py
```

### Pattern de Migration

```python
# src/core/migrations/migration_002_add_quality_score.py

MIGRATION_ID = "002"
MIGRATION_NAME = "add_quality_score"

async def up(db: Database):
    """Appliquer la migration."""
    await db.execute(
        "ALTER TABLE notes ADD COLUMN quality_score INTEGER"
    )
    await db.execute(
        "ALTER TABLE notes ADD COLUMN last_review_at TIMESTAMP"
    )
    await db.commit()

async def down(db: Database):
    """Rollback la migration (si possible)."""
    # SQLite ne supporte pas DROP COLUMN facilement
    # Nécessite de recréer la table
    pass

async def check(db: Database) -> bool:
    """Vérifier si la migration est déjà appliquée."""
    cursor = await db.execute("PRAGMA table_info(notes)")
    columns = [row[1] for row in await cursor.fetchall()]
    return "quality_score" in columns
```

### Exécuter les Migrations

```bash
# Vérifier le statut des migrations
python -m src.core.migrations status

# Appliquer les migrations en attente
python -m src.core.migrations up

# Rollback la dernière migration
python -m src.core.migrations down
```

---

## Commandes de Diagnostic

```bash
# Ouvrir le shell SQLite
sqlite3 data/scapin.db

# Voir le schéma
sqlite3 data/scapin.db ".schema"

# Stats des tables
sqlite3 data/scapin.db "SELECT name, (SELECT COUNT(*) FROM notes) as count FROM sqlite_master WHERE type='table';"

# Taille de la DB
ls -lh data/scapin.db

# Vérifier l'intégrité
sqlite3 data/scapin.db "PRAGMA integrity_check;"

# Stats FAISS
python -c "
import faiss
idx = faiss.read_index('data/faiss/notes.index')
print(f'Vectors: {idx.ntotal}')
print(f'Dimension: {idx.d}')
"

# Reconstruire l'index FAISS (via API)
curl -X POST http://localhost:8000/api/notes/reindex
```

---

## Performance

### Index Recommandés

```sql
-- Toujours indexer les colonnes utilisées dans WHERE, ORDER BY, JOIN
CREATE INDEX idx_notes_folder ON notes(folder_path);
CREATE INDEX idx_notes_updated ON notes(updated_at DESC);
CREATE INDEX idx_queue_status_priority ON queue_items(status, priority DESC);
```

### Explain Query Plan

```sql
-- Vérifier qu'une requête utilise les index
EXPLAIN QUERY PLAN
SELECT * FROM notes WHERE folder_path = 'Projets/Scapin' ORDER BY updated_at DESC;
```

### Vacuum

```bash
# Compacter la DB (récupérer l'espace des suppressions)
sqlite3 data/scapin.db "VACUUM;"
```

---

## Anti-patterns DB

| ❌ Ne pas faire | ✅ Faire |
|-----------------|----------|
| `SELECT *` sans LIMIT | `SELECT ... LIMIT n` |
| Requête dans une boucle | Batch query ou JOIN |
| Index sur toutes les colonnes | Index sur colonnes filtrées/triées |
| Stocker des blobs volumineux | Stocker le chemin du fichier |
| Transactions longues | Transactions courtes et atomiques |
| Ignorer les erreurs de contrainte | Gérer UNIQUE violations |

---

## Fichiers Clés

| Fichier | Rôle |
|---------|------|
| `src/core/database.py` | Wrapper SQLite async |
| `src/passepartout/note_manager.py` | CRUD notes |
| `src/passepartout/faiss_index.py` | Index vectoriel |
| `src/core/migrations/` | Scripts de migration |
