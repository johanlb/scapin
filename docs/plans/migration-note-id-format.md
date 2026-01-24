# Plan : Migration du format note_id

**Objectif** : Changer le format `note_id` de `filename` vers `chemin/filename` pour éliminer les 14 collisions de noms entre dossiers.

**Contexte** : 855 fichiers .md synchronisés, mais seulement 841 dans l'index car 14 notes ont le même nom dans des dossiers différents (ex: "AFRASIA BANK.md" dans 2 dossiers).

---

## Analyse des Risques

### Risques critiques identifiés

| Risque | Impact | Mitigation |
|--------|--------|------------|
| **Clés étrangères SQLite** | `merge_target_id` référence des `note_id` | Migration atomique avec UPDATE des FK |
| **Cache en mémoire** | `_note_cache` utilise `note_id` comme clé | Clear cache après migration |
| **Index FAISS** | `doc_id` = `note_id` | Rebuild complet obligatoire |
| **Routes API avec slashes** | `/api/notes/Notes/AFRASIA` mal interprété | URL encoding (déjà en place) |
| **Wikilinks** | `[[Note]]` vs `[[Folder/Note]]` | Backward compat pour résolution |

### Fichiers critiques (confirmation Johan requise)

Selon CLAUDE.md, ces fichiers nécessitent confirmation avant modification :
- `src/passepartout/note_manager.py` ✓ (coeur de la migration)

---

## Phase 0 : Préparation et Diagnostic

### 0.1 Backup complet
```bash
# SQLite metadata
cp data/notes_meta.db data/notes_meta.db.backup.$(date +%Y%m%d)

# Mapping Apple Notes
cp ~/Documents/Scapin/Notes/apple_notes_sync.json \
   ~/Documents/Scapin/Notes/apple_notes_sync.json.backup.$(date +%Y%m%d)

# Index metadata (JSON léger)
cp ~/Documents/Scapin/Notes/.scapin_notes_meta.json \
   ~/Documents/Scapin/Notes/.scapin_notes_meta.json.backup.$(date +%Y%m%d)
```

### 0.2 Script de diagnostic
**Fichier** : `scripts/migration/note_id_diagnostic.py`

```python
"""Diagnostic des collisions note_id avant migration."""
from pathlib import Path
from collections import defaultdict

def find_collisions(notes_dir: Path) -> dict[str, list[Path]]:
    """Trouve les fichiers avec le même nom dans différents dossiers."""
    by_stem: dict[str, list[Path]] = defaultdict(list)
    for f in notes_dir.rglob("*.md"):
        if not any(p.startswith(".") or p == "_Supprimées" for p in f.parts):
            by_stem[f.stem].append(f)
    return {k: v for k, v in by_stem.items() if len(v) > 1}

def generate_mapping(notes_dir: Path) -> dict[str, str]:
    """Génère le mapping old_id -> new_id pour toutes les notes."""
    mapping = {}
    for f in notes_dir.rglob("*.md"):
        if not any(p.startswith(".") or p == "_Supprimées" for p in f.parts):
            old_id = f.stem
            new_id = str(f.relative_to(notes_dir).with_suffix(""))
            mapping[old_id] = new_id  # Note: écrase si collision (attendu)
    return mapping
```

**Output attendu** :
- Liste des 14 collisions avec leurs chemins
- Mapping JSON `old_id → new_id` pour la migration SQLite

---

## Phase 1 : Modification NoteManager

**Fichier** : `src/passepartout/note_manager.py`

### 1.1 Nouvelle fonction de génération note_id

```python
def _path_to_note_id(self, file_path: Path) -> str:
    """
    Convertit un chemin de fichier en note_id.

    Format: chemin/relatif/sans/extension
    Exemple: "Projets/Scapin/Architecture" pour "Projets/Scapin/Architecture.md"
    """
    rel_path = file_path.relative_to(self.notes_dir)
    # Normaliser les séparateurs (Windows compat)
    return str(rel_path.with_suffix("")).replace("\\", "/")
```

### 1.2 Modifications requises

| Méthode | Ligne | Modification |
|---------|-------|--------------|
| `_read_note_file()` | ~2234 | `note_id = self._path_to_note_id(file_path)` |
| `_get_note_path()` | ~2072 | Reconstruire path depuis note_id avec `/` |
| `get_note()` | ~1567 | Ajouter fallback pour ancien format |
| `create_note()` | ~568 | Inclure subfolder dans note_id généré |
| `_rebuild_metadata_index()` | ~486 | Utiliser nouveau format |

### 1.3 Backward compatibility (temporaire)

```python
def get_note(self, note_id: str) -> Optional[Note]:
    """Récupère une note par ID (supporte ancien et nouveau format)."""
    # Nouveau format : essayer directement
    if "/" in note_id:
        return self._get_note_by_path(note_id)

    # Ancien format : chercher le fichier correspondant
    # ATTENTION: Peut retourner le mauvais fichier si collision
    for path in self.notes_dir.rglob(f"{note_id}.md"):
        if _is_visible_note_path(path):
            return self._read_note_file(path)

    return None
```

### 1.4 Tests unitaires requis

**Fichier** : `tests/unit/test_note_id_migration.py`

```python
class TestNoteIdFormat:
    """Tests pour le nouveau format note_id."""

    def test_path_to_note_id_simple(self, manager, tmp_path):
        """Test conversion simple."""
        file = tmp_path / "notes" / "Test.md"
        assert manager._path_to_note_id(file) == "Test"

    def test_path_to_note_id_nested(self, manager, tmp_path):
        """Test avec sous-dossier."""
        file = tmp_path / "notes" / "Projets" / "Scapin" / "Arch.md"
        assert manager._path_to_note_id(file) == "Projets/Scapin/Arch"

    def test_get_note_new_format(self, manager):
        """Test récupération avec nouveau format."""
        note = manager.get_note("Projets/Scapin/Architecture")
        assert note is not None

    def test_get_note_old_format_fallback(self, manager):
        """Test fallback ancien format."""
        note = manager.get_note("Architecture")  # Sans chemin
        assert note is not None  # Doit trouver via rglob

    def test_collision_resolved(self, manager, tmp_path):
        """Test que les collisions sont résolues."""
        # Créer 2 notes avec le même nom
        (tmp_path / "notes" / "A" / "Note.md").parent.mkdir(parents=True)
        (tmp_path / "notes" / "B" / "Note.md").parent.mkdir(parents=True)
        (tmp_path / "notes" / "A" / "Note.md").write_text("Content A")
        (tmp_path / "notes" / "B" / "Note.md").write_text("Content B")

        manager.refresh_index()

        # Les deux doivent être distinctes
        note_a = manager.get_note("A/Note")
        note_b = manager.get_note("B/Note")
        assert note_a.content != note_b.content
```

---

## Phase 2 : Migration SQLite

**Fichier** : `src/passepartout/note_metadata.py`

### 2.1 Incrémenter version

```python
SCHEMA_VERSION = 4  # Était 3
```

### 2.2 Migration v3 → v4

```python
def _migrate_v3_to_v4(self, cursor: sqlite3.Cursor) -> None:
    """
    Migrate note_id format: filename -> relative_path/filename

    Strategy:
    1. Scanner le filesystem pour construire le mapping
    2. UPDATE note_id en batch (avec gestion des collisions)
    3. UPDATE merge_target_id (clé étrangère)
    4. Supprimer les entrées orphelines (notes supprimées)
    """
    logger.info("Migrating database schema from v3 to v4 (note_id path format)")

    # 1. Construire le mapping depuis le filesystem
    notes_dir = Path(self.db_path).parent.parent / "Notes"
    if not notes_dir.exists():
        notes_dir = Path.home() / "Documents" / "Scapin" / "Notes"

    old_to_new: dict[str, str] = {}
    for f in notes_dir.rglob("*.md"):
        if not any(p.startswith(".") or p == "_Supprimées" for p in f.parts):
            old_id = f.stem
            new_id = str(f.relative_to(notes_dir).with_suffix(""))
            # En cas de collision, garder le premier (les autres seront orphelins)
            if old_id not in old_to_new:
                old_to_new[old_id] = new_id

    # 2. UPDATE note_id
    for old_id, new_id in old_to_new.items():
        cursor.execute(
            "UPDATE note_metadata SET note_id = ? WHERE note_id = ?",
            (new_id, old_id)
        )

    # 3. UPDATE merge_target_id (clé étrangère)
    for old_id, new_id in old_to_new.items():
        cursor.execute(
            "UPDATE note_metadata SET merge_target_id = ? WHERE merge_target_id = ?",
            (new_id, old_id)
        )

    # 4. Log des statistiques
    cursor.execute("SELECT COUNT(*) FROM note_metadata")
    total = cursor.fetchone()[0]
    logger.info(
        f"Migration v3→v4 completed: {len(old_to_new)} mappings, {total} records"
    )
```

### 2.3 Appeler la migration

```python
# Dans _initialize_db(), après les autres migrations :
if current_version < 4:
    self._migrate_v3_to_v4(cursor)
```

### 2.4 Test de migration

**Fichier** : `tests/unit/test_note_metadata.py` (ajouter)

```python
def test_migrate_v3_to_v4(tmp_path):
    """Test migration du format note_id."""
    # Setup: créer une DB v3 avec des données
    db_path = tmp_path / "notes_meta.db"
    # ... (créer schéma v3, insérer données avec ancien format)

    # Exécuter migration
    store = NoteMetadataStore(db_path)

    # Vérifier
    meta = store.get_metadata("Projets/Scapin/Architecture")  # Nouveau format
    assert meta is not None
```

---

## Phase 3 : Vector Store FAISS

**Approche** : Rebuild complet (plus sûr que migration in-place)

### 3.1 Rebuild automatique

Le rebuild utilise `NoteManager` qui génère maintenant les nouveaux `note_id`.

```bash
# Via API (recommandé)
curl -X POST http://localhost:8000/api/notes/reindex

# Ou via code
manager = get_note_manager()
manager.rebuild_index()
```

### 3.2 Vérification

```python
# Vérifier que l'index utilise les nouveaux IDs
store = VectorStore(data_dir / "faiss")
results = store.search("test query", k=5)
for doc_id, score in results:
    assert "/" in doc_id or doc_id.count("/") == 0  # Soit nouveau format, soit racine
```

---

## Phase 4 : Apple Notes Sync

**Fichier** : `src/integrations/apple/notes_sync.py`

### 4.1 Analyse

Le mapping JSON utilise déjà `scapin_path` (chemin complet avec extension) :
```json
{
  "x-coredata://...": {
    "scapin_path": "Projets/Scapin/Architecture.md",
    "apple_folder": "Projets/Scapin"
  }
}
```

### 4.2 Modifications

Aucune modification requise au format de stockage.

Vérifier que les fonctions qui extraient le `note_id` depuis `scapin_path` utilisent :
```python
note_id = scapin_path.removesuffix(".md")  # Pas juste Path(scapin_path).stem
```

### 4.3 Test E2E sync

```bash
# 1. Créer une note dans Apple Notes (dossier "Test")
# 2. Sync
curl -X POST http://localhost:8000/api/notes/sync
# 3. Vérifier que le note_id inclut le chemin
curl http://localhost:8000/api/notes/Test/MaNote
```

---

## Phase 5 : Frontend

**Fichiers** :
- `web/src/routes/memoires/[...path]/+page.svelte`
- `web/src/lib/api/client.ts`

### 5.1 Route memoires

La route `[...path]` capture déjà les chemins avec slashes. Vérifier :

```typescript
// Avant (si existant)
const noteId = pathParts[pathParts.length - 1];  // "Architecture"

// Après
const noteId = notePath;  // "Projets/Scapin/Architecture"
```

### 5.2 Appels API

`encodeURIComponent` est déjà utilisé partout - aucun changement requis.

Vérification :
```typescript
// "Projets/Scapin/Architecture" devient "Projets%2FScapin%2FArchitecture"
const url = `/api/notes/${encodeURIComponent(noteId)}`;
```

### 5.3 Test E2E

**Fichier** : `web/e2e/pages/memoires.spec.ts` (ajouter)

```typescript
test('can navigate to nested note', async ({ page }) => {
    await page.goto('/memoires');

    // Cliquer sur un dossier, puis une note
    await page.click('[data-testid="folder-Projets"]');
    await page.click('[data-testid="note-Projets/Scapin/Architecture"]');

    // Vérifier l'URL
    await expect(page).toHaveURL(/memoires\/Projets%2FScapin%2FArchitecture/);

    // Vérifier le contenu
    await expect(page.locator('[data-testid="note-title"]')).toBeVisible();
});
```

---

## Phase 6 : Tests et Validation

### 6.1 Tests automatisés

```bash
# Backend complet
.venv/bin/pytest tests/ -v --tb=short

# Tests spécifiques migration
.venv/bin/pytest tests/unit/test_note_id_migration.py -v
.venv/bin/pytest tests/unit/test_note_metadata.py -v
.venv/bin/pytest tests/unit/test_apple_notes_sync.py -v

# E2E
cd web && npx playwright test e2e/pages/memoires.spec.ts

# Qualité
.venv/bin/ruff check src/
cd web && npm run check
```

### 6.2 Checklist validation manuelle

```
□ Compteur UI affiche 855 notes (était 841)
□ Les 14 notes en collision sont maintenant distinctes
□ Créer une note dans un subfolder → note_id inclut le chemin
□ Recherche full-text fonctionne
□ Recherche sémantique fonctionne
□ Sync Apple Notes (créer dans Apple → apparaît dans Scapin)
□ Retouche sur une note avec chemin fonctionne
□ Review (lecture) sur une note fonctionne
□ Wikilinks `[[Note]]` résolvent correctement
□ Navigation UI vers note imbriquée fonctionne
□ Logs : aucun ERROR/WARNING nouveau
```

---

## Commits (un par phase)

Format conforme à `/workflow` :

1. `feat(passepartout): add path-based note_id generation`
2. `feat(passepartout): migrate note_metadata schema v3→v4`
3. `chore(passepartout): rebuild FAISS index with new note_id format`
4. `fix(frontend): update note_id extraction for path format`
5. `test: add migration and collision tests`

---

## Rollback

| Phase | Commande |
|-------|----------|
| Phase 1 | `git checkout src/passepartout/note_manager.py` |
| Phase 2 | `cp data/notes_meta.db.backup.YYYYMMDD data/notes_meta.db` |
| Phase 3 | Rebuild FAISS avec ancienne version du code |
| Phase 5 | `git checkout web/src/` |

**Point de non-retour** : Après Phase 2 si des données ont été modifiées en production.

---

## Fichiers à modifier (résumé)

| Fichier | Type | Changement |
|---------|------|------------|
| `src/passepartout/note_manager.py` | Backend | `_path_to_note_id()`, `get_note()`, etc. |
| `src/passepartout/note_metadata.py` | Backend | Migration v3→v4 |
| `web/src/routes/memoires/[...path]/+page.svelte` | Frontend | Extraction noteId |
| `scripts/migration/note_id_diagnostic.py` | Script | Nouveau - diagnostic |
| `tests/unit/test_note_id_migration.py` | Test | Nouveau - tests migration |
| `web/e2e/pages/memoires.spec.ts` | Test E2E | Test navigation imbriquée |
