# Plan : Migration + 10 Améliorations Notes & UI

> Demandes utilisateur du 24 janvier 2026
> **Conforme aux directives** : CLAUDE.md v3.3, /workflow, /api, /ui, /tests, /db

---

## ⚠️ Fichiers Critiques (Confirmation Requise)

Selon CLAUDE.md, ces fichiers nécessitent **confirmation explicite de Johan** :

| Fichier | Phase | Modification |
|---------|-------|--------------|
| `src/passepartout/note_manager.py` | #1, #5 | Seuil recherche, sync date |
| `src/passepartout/retouche_reviewer.py` | Migration, #3 | Fusion NoteReviewer + templates |
| `src/passepartout/note_reviewer.py` | Migration | **Suppression** après fusion |

**Les autres fichiers peuvent être modifiés sans confirmation.**

---

## Vue d'Ensemble

Ce plan combine :
1. **Migration NoteReviewer → RetoucheReviewer** (consolidation, -700 lignes)
2. **10 améliorations Notes & UI** (features et fixes)

La migration est un **prérequis** car elle consolide la base de code avant les améliorations.

---

## Phase 0 : Migration NoteReviewer → RetoucheReviewer

### Objectif
Fusionner `NoteReviewer` dans `RetoucheReviewer` pour éliminer le doublon de processus tout en préservant toutes les fonctionnalités.

### Fonctionnalités à migrer

| Fonctionnalité | Source | Usage |
|----------------|--------|-------|
| **HygieneMetrics** | note_reviewer.py:94-108 | Métriques qualité |
| **_scrub_content()** | note_reviewer.py:536-548 | Économie tokens IA |
| **_calculate_hygiene_metrics()** | note_reviewer.py:433-529 | Détection problèmes |
| **_check_temporal_references()** | note_reviewer.py:660-698 | Contenu obsolète |
| **_check_completed_tasks()** | note_reviewer.py:701-737 | Tâches terminées |
| **_check_missing_links()** | note_reviewer.py:739-772 | Connectivité |
| **_check_formatting()** | note_reviewer.py:774-801 | Corrections mécaniques |
| **CrossSourceEngine** | note_reviewer.py:362-431 | Contexte externe |

### Types à unifier
```python
# Mapping ActionType → RetoucheAction
ADD, UPDATE → ENRICH
REMOVE → CLEANUP
LINK → SUGGEST_LINKS
ARCHIVE → FLAG_OBSOLETE
FORMAT → FORMAT (nouveau)
VALIDATE → VALIDATE (nouveau)
FIX_LINKS → FIX_LINKS (nouveau)
```

### Stratégie de Rollback

En cas de problème après un commit de migration :
```bash
# Identifier le commit problématique
git log --oneline -10

# Revert du commit spécifique
git revert <commit-hash>

# OU rollback complet de la migration
git revert --no-commit M1..M9
git commit -m "revert: rollback migration NoteReviewer"
```

### Commits Migration (9 commits)

Chaque commit DOIT passer les tests avant de continuer au suivant.

| # | Commit | Fichiers | Validation |
|---|--------|----------|------------|
| M1 | `refactor(passepartout): ajouter types HygieneMetrics à RetoucheReviewer` | `retouche_reviewer.py` | `ruff check && pytest tests/passepartout/test_retouche_reviewer.py` |
| M2 | `refactor(passepartout): migrer méthodes utilitaires vers RetoucheReviewer` | `retouche_reviewer.py` | idem |
| M3 | `refactor(passepartout): migrer analyses rule-based vers RetoucheReviewer` | `retouche_reviewer.py` | idem |
| M4 | `refactor(passepartout): intégrer CrossSourceEngine dans RetoucheReviewer` | `retouche_reviewer.py` | idem |
| M5 | `refactor(passepartout): adapter background_worker pour RetoucheReviewer unifié` | `background_worker.py` | `pytest tests/passepartout/` |
| M6 | `refactor(cli): adapter commande pending pour RetoucheReviewer` | `cli.py` | `pkm notes pending list` |
| M7 | `docs(passepartout): mettre à jour exports et documentation` | `__init__.py`, docs | — |
| M8 | `test(passepartout): adapter tests pour RetoucheReviewer unifié` | `test_retouche_reviewer.py` | `pytest tests/passepartout/ -v` |
| M9 | `refactor(passepartout): supprimer NoteReviewer obsolète` | `note_reviewer.py` ❌ | **Test complet** : `pytest tests/` |

### Test de Non-Régression (après M9)

```bash
# 1. Vérifier que RetoucheReviewer fonctionne
.venv/bin/python -c "
from src.passepartout.retouche_reviewer import RetoucheReviewer, HygieneMetrics
print('Import OK')
"

# 2. Tester une retouche complète
.venv/bin/python -m src.frontin.cli notes review --process --limit 1 --force

# 3. Vérifier les checks d'hygiène
.venv/bin/python -m src.frontin.cli notes pending list

# 4. Tests unitaires complets
.venv/bin/pytest tests/passepartout/ -v

# 5. Ruff
.venv/bin/ruff check src/passepartout/
```

### Bilan
- ~300 lignes ajoutées à `retouche_reviewer.py`
- ~1000 lignes supprimées (`note_reviewer.py`)
- **Bilan net : -700 lignes**

---

## Résumé des 10 Points

| # | Demande | Complexité | Type |
|---|---------|------------|------|
| 1 | Recherche "Ramun" mal classée | Moyenne-Haute | Fix |
| 2 | Afficher dossier de la note | Simple | UI |
| 3 | Restructurer selon modèle en retouche | Complexe | Feature |
| 4 | Clarifier "facteur de facilité" | Simple | Doc/UI |
| 5 | Afficher ancienneté sync Apple Notes | Moyenne | Feature |
| 6 | Modifier metadata (tous champs) | Moyenne | Feature |
| 7 | Workflow bouton Hygiène | Moyenne | Feature |
| 8 | Workflow bouton SM-2 | — | Déjà OK |
| 9 | Bouton créer nouvelle note | Moyenne | Feature |
| 10 | Activer NoteEnricher (recherche web) | Moyenne | Feature |

---

## Point 1 : Recherche - Problème de Pertinence

### Problème Identifié

La recherche sur "Ramun" retourne "RABAYE K et hia" avec un **score de 93.8%** alors que cette note ne contient même pas le mot.

**Causes** :
1. Aucun seuil de score : FAISS retourne tous les résultats
2. Sémantique uniquement : Pas de vérification full-text
3. Score converti sans validation : `1/(1+0.065) = 93.8%`

### Solution (3 niveaux)

**Niveau 1 : Seuil de Score Minimum 40%**
```python
# src/passepartout/vector_store.py
MAX_L2_DISTANCE = 1.5  # Rejette si distance > 1.5 (≈40% score)

# src/frontin/api/services/notes_service.py
MIN_SCORE_THRESHOLD = 0.4
```

**Niveau 2 : Boost Titre (+50%)**
```python
# Post-processing dans notes_service.py
if query.lower() in note.title.lower():
    similarity_score *= 1.5
```

### Fichiers à Modifier
- `src/passepartout/vector_store.py` : Param `max_distance`
- `src/passepartout/note_manager.py` : Propager le seuil ⚠️ **Fichier critique**
- `src/frontin/api/services/notes_service.py` : Filtrer + boost

### Tests Requis

```python
# tests/passepartout/test_vector_store.py
class TestSearchThreshold:
    def test_rejects_low_score_results(self, vector_store, sample_notes):
        """Score < 40% ne doit pas être retourné."""
        results = vector_store.search("Ramun", top_k=10, min_score=0.4)
        for note, score in results:
            assert score >= 0.4, f"Score {score} below threshold"

    def test_exact_title_match_boosted(self, vector_store):
        """Titre exact doit être boosté."""
        results = vector_store.search("Ramun", top_k=5)
        # La note "Ramun" doit être en premier si elle existe
        titles = [r[0].title for r in results]
        if "Ramun" in titles:
            assert titles[0] == "Ramun"

    def test_returns_empty_on_no_match(self, vector_store):
        """Requête sans match retourne liste vide."""
        results = vector_store.search("xyzabc123nonexistent", top_k=10, min_score=0.4)
        assert results == []
```

### data-testid pour E2E
- `data-testid="search-input"` : Champ de recherche
- `data-testid="search-result-item"` : Item de résultat
- `data-testid="search-no-results"` : Message aucun résultat

---

## Point 2 : Afficher le Dossier de la Note

### Solution (Svelte 5 conforme /ui)

```svelte
<!-- web/src/routes/memoires/[...path]/+page.svelte -->
<script lang="ts">
    import type { Note } from '$lib/api/types/notes';

    interface Props {
        note: Note;
    }

    let { note }: Props = $props();

    // $derived pour calcul pur (pas $effect)
    const folderPath = $derived(() => {
        if (!note.note_path) return 'Racine';
        const parts = note.note_path.split('/');
        return parts.slice(0, -1).join('/') || 'Racine';
    });
</script>

<div class="note-header">
    <span
        class="folder-path text-sm"
        style="color: var(--color-text-tertiary);"
        data-testid="note-folder-path"
    >
        📁 {folderPath}
    </span>
    <h1>{note.title}</h1>
</div>
```

### Fichiers à Modifier
- `web/src/routes/memoires/[...path]/+page.svelte`

### Tests E2E

```typescript
// web/e2e/pages/memoires.spec.ts
test('displays folder path in note detail', async ({ page }) => {
    await page.goto('/memoires/Personnes/Jean-Dupont');
    await page.waitForSelector('[data-testid="note-folder-path"]');

    const folderPath = page.locator('[data-testid="note-folder-path"]');
    await expect(folderPath).toBeVisible();
    await expect(folderPath).toContainText('Personnes');
});

test('shows "Racine" for root notes', async ({ page }) => {
    // Note à la racine
    await page.goto('/memoires/Note-Racine');
    const folderPath = page.locator('[data-testid="note-folder-path"]');
    await expect(folderPath).toContainText('Racine');
});
```

---

## Point 3 : Restructuration selon Modèle en Retouche

### État Actuel
- `RetoucheReviewer` a une action `STRUCTURE`
- Le SYSTEM_PROMPT contient des règles génériques par type
- **MAIS** : Les notes "Modèle X" du dossier Processus ne sont **pas chargées**

### Solution

```python
# src/passepartout/retouche_reviewer.py

def _load_template_for_type(self, note_type: str) -> str | None:
    """
    Charge la note 'Modèle - Fiche {type}' depuis PKM/Processus.

    Args:
        note_type: Type de note (personne, projet, concept...)

    Returns:
        Contenu du template ou None si non trouvé
    """
    template_paths = [
        f"Personal Knowledge Management/Processus/Modèle - Fiche {note_type.capitalize()}",
        f"Personal Knowledge Management/Processus/Modèle - {note_type.capitalize()}",
    ]

    for path in template_paths:
        template_note = self.notes.get_note(path)
        if template_note:
            return template_note.content

    logger.debug(f"No template found for type {note_type}")
    return None

def _build_retouche_prompt(self, context: RetoucheContext) -> str:
    # ... existing code ...

    # Charger le template
    template_content = self._load_template_for_type(note_type)

    return renderer.render_retouche(
        # ... existing params ...
        template_structure=template_content,
    )
```

### Fichiers à Modifier
- `src/passepartout/retouche_reviewer.py` ⚠️ **Fichier critique**
- `src/sancho/templates/render_retouche.j2` : Section template

### Tests

```python
# tests/passepartout/test_retouche_reviewer.py
class TestTemplateLoading:
    @pytest.fixture
    def mock_note_manager(self):
        manager = MagicMock()
        manager.get_note.return_value = Note(
            note_id="template-personne",
            title="Modèle - Fiche Personne",
            content="## Structure\n- Prénom\n- Fonction\n- Contact"
        )
        return manager

    def test_loads_template_for_known_type(self, reviewer, mock_note_manager):
        reviewer.notes = mock_note_manager
        template = reviewer._load_template_for_type("personne")
        assert template is not None
        assert "Structure" in template

    def test_returns_none_for_unknown_type(self, reviewer, mock_note_manager):
        mock_note_manager.get_note.return_value = None
        template = reviewer._load_template_for_type("inconnu")
        assert template is None
```

---

## Point 4 : Clarifier "Facteur de Facilité"

### Explication SM-2
| Valeur | Signification |
|--------|---------------|
| **2.5** (max) | Note facile → intervalles longs |
| **1.3** (min) | Note difficile → intervalles courts |

### Solution UI (Svelte 5 + Liquid Glass)

```svelte
<!-- web/src/lib/components/notes/ReviewCard.svelte -->
<script lang="ts">
    interface Props {
        metadata: NoteMetadata;
    }

    let { metadata }: Props = $props();

    const efDescription = $derived(() => {
        const ef = metadata.easiness_factor;
        if (ef >= 2.3) return 'Facile';
        if (ef >= 1.8) return 'Moyen';
        return 'Difficile';
    });
</script>

<div class="glass glass-subtle rounded-lg p-2">
    <span
        class="ef-badge"
        title="Facilité de mémorisation (1.3=difficile, 2.5=facile). Influence l'intervalle de révision."
        data-testid="easiness-factor"
    >
        EF: {metadata.easiness_factor.toFixed(1)}
        <span class="ef-label">({efDescription})</span>
    </span>
</div>

<style>
    .ef-badge {
        cursor: help;
        color: var(--color-text-secondary);
    }
    .ef-label {
        font-size: 0.85em;
        color: var(--color-text-tertiary);
    }
</style>
```

### Tests E2E

```typescript
test('displays easiness factor with tooltip', async ({ page }) => {
    await page.goto('/memoires/Test-Note');
    const efBadge = page.locator('[data-testid="easiness-factor"]');

    await expect(efBadge).toBeVisible();
    await expect(efBadge).toHaveAttribute('title', /Facilité de mémorisation/);
});
```

---

## Point 5 : Ancienneté Sync Apple Notes

### Migration DB Requise

```python
# src/core/migrations/migration_004_add_last_synced_at.py
"""Migration: Ajouter champ last_synced_at aux métadonnées de notes."""

MIGRATION_ID = "004"
MIGRATION_NAME = "add_last_synced_at"

async def up(db: Database):
    """Appliquer la migration."""
    await db.execute(
        "ALTER TABLE note_metadata ADD COLUMN last_synced_at TIMESTAMP"
    )
    await db.commit()
    logger.info("Migration 004: Added last_synced_at column")

async def down(db: Database):
    """Rollback - SQLite ne supporte pas DROP COLUMN facilement."""
    logger.warning("Migration 004 down: Manual intervention required")
    # Nécessite de recréer la table sans la colonne

async def check(db: Database) -> bool:
    """Vérifier si la migration est déjà appliquée."""
    cursor = await db.execute("PRAGMA table_info(note_metadata)")
    columns = [row[1] for row in await cursor.fetchall()]
    return "last_synced_at" in columns
```

### Dataclass Update

```python
# src/passepartout/note_metadata.py
@dataclass
class NoteMetadata:
    # ... existing fields ...
    last_synced_at: datetime | None = None  # NULL = jamais synced ou inconnu
```

### Mise à jour lors du sync

```python
# src/passepartout/note_manager.py - sync_apple_notes()
async def sync_apple_notes(self) -> SyncResult:
    # ... existing code ...

    for note in synced_notes:
        metadata = self.metadata_store.get(note.note_id)
        if metadata:
            metadata.last_synced_at = datetime.now(timezone.utc)
            self.metadata_store.save(metadata)

    # ... rest of method ...
```

### UI (Svelte 5)

```svelte
<script lang="ts">
    import { formatRelativeTime } from '$lib/utils/date';

    interface Props {
        metadata: NoteMetadata;
    }

    let { metadata }: Props = $props();

    const syncAge = $derived(() => {
        if (!metadata.last_synced_at) return null;
        return formatRelativeTime(new Date(metadata.last_synced_at));
    });
</script>

{#if syncAge}
    <span
        class="sync-info text-sm"
        style="color: var(--color-text-tertiary);"
        data-testid="sync-age"
    >
        🔄 Sync: {syncAge}
    </span>
{/if}
```

### Fichiers à Modifier
- `src/core/migrations/migration_004_add_last_synced_at.py` : **Créer**
- `src/passepartout/note_metadata.py` : Ajouter champ
- `src/passepartout/note_manager.py` ⚠️ **Fichier critique** : Mettre à jour lors sync
- `web/src/lib/api/client.ts` : Type `NoteMetadata`
- `web/src/routes/memoires/[...path]/+page.svelte` : Afficher

### Tests

```python
# tests/passepartout/test_note_metadata.py
class TestLastSyncedAt:
    def test_sync_updates_last_synced_at(self, note_manager, metadata_store):
        """Sync doit mettre à jour last_synced_at."""
        note_id = "test-note"
        metadata = metadata_store.get(note_id)
        assert metadata.last_synced_at is None

        note_manager.sync_apple_notes()

        metadata = metadata_store.get(note_id)
        assert metadata.last_synced_at is not None
        assert metadata.last_synced_at <= datetime.now(timezone.utc)

    def test_existing_notes_have_null_last_synced(self, metadata_store):
        """Notes existantes avant migration ont NULL."""
        old_note_metadata = metadata_store.get("old-note")
        assert old_note_metadata.last_synced_at is None
```

---

## Point 6 : Modifier Metadata (Tous les Champs)

### Champs Éditables

| Champ | Type | Description |
|-------|------|-------------|
| `importance` | enum | critical, high, normal, low, archive |
| `auto_enrich` | bool | Activer/désactiver enrichissement IA |
| `note_type` | enum | personne, projet, concept, etc. |
| `skip_revision` | bool | Exclure des révisions SM-2 |
| `web_search_enabled` | bool | Autoriser recherche web |

### Backend (conforme /api)

```python
# src/frontin/api/models/notes.py
from pydantic import BaseModel, Field
from typing import Optional
from src.passepartout.note_types import NoteType, ImportanceLevel

class NoteMetadataUpdateRequest(BaseModel):
    """Request body for PATCH /notes/{id}/metadata."""
    importance: Optional[ImportanceLevel] = None
    auto_enrich: Optional[bool] = None
    note_type: Optional[NoteType] = None
    skip_revision: Optional[bool] = None
    web_search_enabled: Optional[bool] = None

    class Config:
        use_enum_values = True


# src/frontin/api/routers/notes.py
from fastapi import APIRouter, Depends, HTTPException, Request
from src.frontin.api.models.responses import APIResponse
from src.core.exceptions import ScapinError
from src.monitoring.logger import get_logger

logger = get_logger("frontin.api.notes")

@router.patch("/{note_id}/metadata", response_model=APIResponse[NoteMetadataResponse])
async def update_note_metadata(
    request: Request,
    note_id: str,
    updates: NoteMetadataUpdateRequest,
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[NoteMetadataResponse]:
    """
    Mettre à jour les métadonnées d'une note.

    Seuls les champs fournis sont mis à jour (PATCH semantics).
    """
    correlation_id = request.headers.get("X-Correlation-ID", "unknown")

    try:
        metadata = await service.update_metadata(note_id, updates)
        logger.info(
            f"Metadata updated for note {note_id}",
            extra={"correlation_id": correlation_id, "note_id": note_id}
        )
        return APIResponse(success=True, data=metadata)
    except ScapinError as e:
        logger.error(
            f"Failed to update metadata: {e}",
            extra={"correlation_id": correlation_id, "note_id": note_id},
            exc_info=True
        )
        raise HTTPException(status_code=400, detail=e.message) from e
```

### Frontend (Svelte 5 + Liquid Glass)

```svelte
<!-- web/src/lib/components/notes/MetadataEditor.svelte -->
<script lang="ts">
    import { updateNoteMetadata } from '$lib/api/notes';
    import type { NoteMetadata, NoteType, ImportanceLevel } from '$lib/api/types/notes';

    interface Props {
        noteId: string;
        metadata: NoteMetadata;
        onupdate?: (metadata: NoteMetadata) => void;
    }

    let { noteId, metadata, onupdate }: Props = $props();

    let saving = $state(false);
    let error = $state<string | null>(null);

    // État local pour édition
    let importance = $state(metadata.importance);
    let noteType = $state(metadata.note_type);
    let autoEnrich = $state(metadata.auto_enrich);
    let skipRevision = $state(metadata.skip_revision ?? false);
    let webSearchEnabled = $state(metadata.web_search_enabled ?? false);

    async function saveMetadata() {
        saving = true;
        error = null;

        try {
            const updated = await updateNoteMetadata(noteId, {
                importance,
                note_type: noteType,
                auto_enrich: autoEnrich,
                skip_revision: skipRevision,
                web_search_enabled: webSearchEnabled,
            });
            onupdate?.(updated);
        } catch (e) {
            error = e instanceof Error ? e.message : 'Erreur inconnue';
        } finally {
            saving = false;
        }
    }
</script>

<div class="glass glass-subtle rounded-xl p-4" data-testid="metadata-editor">
    <h3 class="text-lg font-medium mb-4">Métadonnées</h3>

    {#if error}
        <div class="text-red-500 mb-4" role="alert">{error}</div>
    {/if}

    <div class="space-y-4">
        <label class="block">
            <span class="text-sm" style="color: var(--color-text-secondary);">Importance</span>
            <select
                bind:value={importance}
                onchange={saveMetadata}
                disabled={saving}
                class="glass-input w-full mt-1"
                data-testid="metadata-importance"
            >
                <option value="critical">Critique</option>
                <option value="high">Haute</option>
                <option value="normal">Normale</option>
                <option value="low">Basse</option>
                <option value="archive">Archive</option>
            </select>
        </label>

        <label class="block">
            <span class="text-sm" style="color: var(--color-text-secondary);">Type de note</span>
            <select
                bind:value={noteType}
                onchange={saveMetadata}
                disabled={saving}
                class="glass-input w-full mt-1"
                data-testid="metadata-note-type"
            >
                <option value="personne">Personne</option>
                <option value="projet">Projet</option>
                <option value="concept">Concept</option>
                <option value="reunion">Réunion</option>
                <option value="entite">Entité</option>
                <option value="souvenir">Souvenir</option>
            </select>
        </label>

        <label class="flex items-center gap-2">
            <input
                type="checkbox"
                bind:checked={autoEnrich}
                onchange={saveMetadata}
                disabled={saving}
                data-testid="metadata-auto-enrich"
            />
            <span>Enrichissement automatique</span>
        </label>

        <label class="flex items-center gap-2">
            <input
                type="checkbox"
                bind:checked={skipRevision}
                onchange={saveMetadata}
                disabled={saving}
                data-testid="metadata-skip-revision"
            />
            <span>Exclure des révisions</span>
        </label>

        <label class="flex items-center gap-2">
            <input
                type="checkbox"
                bind:checked={webSearchEnabled}
                onchange={saveMetadata}
                disabled={saving}
                data-testid="metadata-web-search"
            />
            <span>Autoriser recherche web</span>
        </label>
    </div>
</div>
```

### Client TypeScript

```typescript
// web/src/lib/api/notes.ts
export interface NoteMetadataUpdateRequest {
    importance?: ImportanceLevel;
    note_type?: NoteType;
    auto_enrich?: boolean;
    skip_revision?: boolean;
    web_search_enabled?: boolean;
}

export async function updateNoteMetadata(
    noteId: string,
    updates: NoteMetadataUpdateRequest
): Promise<NoteMetadata> {
    const response = await apiClient.patch<APIResponse<NoteMetadata>>(
        `/api/notes/${noteId}/metadata`,
        updates
    );
    if (!response.success || !response.data) {
        throw new Error(response.error ?? 'Failed to update metadata');
    }
    return response.data;
}
```

### Tests

```python
# tests/frontin/api/test_notes.py
class TestPatchMetadata:
    def test_updates_single_field(self, client, mock_service):
        """PATCH avec un seul champ ne touche pas les autres."""
        response = client.patch(
            "/api/notes/test-id/metadata",
            json={"importance": "high"}
        )
        assert response.status_code == 200
        mock_service.update_metadata.assert_called_once()

    def test_validates_enum_values(self, client):
        """Valeurs invalides retournent 422."""
        response = client.patch(
            "/api/notes/test-id/metadata",
            json={"importance": "invalid_value"}
        )
        assert response.status_code == 422

    def test_returns_404_for_unknown_note(self, client, mock_service):
        """Note inexistante retourne 404."""
        mock_service.update_metadata.side_effect = ScapinError("Note not found")
        response = client.patch(
            "/api/notes/unknown/metadata",
            json={"importance": "high"}
        )
        assert response.status_code == 400
```

```typescript
// web/e2e/pages/memoires.spec.ts
test('can edit note metadata', async ({ page }) => {
    await page.goto('/memoires/Test-Note');

    // Ouvrir l'éditeur
    const editor = page.locator('[data-testid="metadata-editor"]');
    await expect(editor).toBeVisible();

    // Changer l'importance
    await page.selectOption('[data-testid="metadata-importance"]', 'high');

    // Vérifier la sauvegarde (pas de spinner après)
    await page.waitForSelector('[data-testid="metadata-importance"]:not([disabled])');

    // Recharger et vérifier la persistance
    await page.reload();
    const importance = page.locator('[data-testid="metadata-importance"]');
    await expect(importance).toHaveValue('high');
});
```

---

## Point 7 : Workflow Bouton Hygiène 🧹

### Prérequis : Migration (Phase 0)
Le backend hygiène existe dans `NoteReviewer` et sera migré vers `RetoucheReviewer`.

### Backend (Post-Migration)

```python
# src/frontin/api/models/notes.py
class HygieneIssue(BaseModel):
    """Un problème d'hygiène détecté."""
    type: str  # 'broken_link', 'temporal_ref', 'completed_task', 'formatting'
    severity: str  # 'low', 'medium', 'high'
    detail: str
    location: Optional[str] = None
    auto_fixable: bool = False
    fix_applied: bool = False

class HygieneResult(BaseModel):
    """Résultat d'un check d'hygiène."""
    note_id: str
    health_score: int  # 0-100
    issues: list[HygieneIssue]
    metrics: dict  # word_count, section_count, etc.


# src/frontin/api/routers/notes.py
@router.post("/{note_id}/hygiene", response_model=APIResponse[HygieneResult])
async def run_note_hygiene(
    request: Request,
    note_id: str,
    auto_fix: bool = Query(False, description="Appliquer les corrections automatiques"),
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[HygieneResult]:
    """
    Exécute les checks d'hygiène rule-based (sans IA).

    Vérifie : liens cassés, références temporelles, tâches terminées, formatage.
    """
    correlation_id = request.headers.get("X-Correlation-ID", "unknown")

    try:
        result = await service.run_hygiene(note_id, auto_fix=auto_fix)
        logger.info(
            f"Hygiene check completed for {note_id}",
            extra={
                "correlation_id": correlation_id,
                "note_id": note_id,
                "health_score": result.health_score,
                "issues_count": len(result.issues)
            }
        )
        return APIResponse(success=True, data=result)
    except ScapinError as e:
        logger.error(f"Hygiene check failed: {e}", extra={"correlation_id": correlation_id})
        raise HTTPException(status_code=400, detail=e.message) from e
```

### Frontend

```svelte
<!-- web/src/lib/components/notes/HygieneButton.svelte -->
<script lang="ts">
    import { runNoteHygiene } from '$lib/api/notes';
    import type { HygieneResult } from '$lib/api/types/notes';

    interface Props {
        noteId: string;
        onresult?: (result: HygieneResult) => void;
    }

    let { noteId, onresult }: Props = $props();

    let loading = $state(false);
    let result = $state<HygieneResult | null>(null);
    let error = $state<string | null>(null);

    async function runHygiene() {
        loading = true;
        error = null;

        try {
            result = await runNoteHygiene(noteId, { autoFix: true });
            onresult?.(result);
        } catch (e) {
            error = e instanceof Error ? e.message : 'Erreur';
        } finally {
            loading = false;
        }
    }

    const healthColor = $derived(() => {
        if (!result) return 'var(--color-text-secondary)';
        if (result.health_score >= 80) return 'var(--color-success)';
        if (result.health_score >= 50) return 'var(--color-warning)';
        return 'var(--color-error)';
    });
</script>

<button
    onclick={runHygiene}
    disabled={loading}
    class="glass glass-interactive rounded-lg px-4 py-2"
    data-testid="hygiene-button"
>
    {#if loading}
        <span class="spinner" />
    {:else}
        🧹 Hygiène
    {/if}
</button>

{#if result}
    <div class="glass glass-subtle rounded-lg p-4 mt-4" data-testid="hygiene-result">
        <h4 style="color: {healthColor}">
            Score : {result.health_score}%
        </h4>

        {#if result.issues.length === 0}
            <p class="text-green-600">Aucun problème détecté</p>
        {:else}
            <ul class="space-y-2 mt-2">
                {#each result.issues as issue}
                    <li class="text-sm" data-testid="hygiene-issue">
                        <span class="font-medium">{issue.type}</span>: {issue.detail}
                        {#if issue.fix_applied}
                            <span class="text-green-600">✓ Corrigé</span>
                        {/if}
                    </li>
                {/each}
            </ul>
        {/if}
    </div>
{/if}

{#if error}
    <div class="text-red-500 mt-2" role="alert">{error}</div>
{/if}
```

### Tests

```python
class TestHygieneEndpoint:
    def test_returns_health_score(self, client, mock_service):
        mock_service.run_hygiene.return_value = HygieneResult(
            note_id="test",
            health_score=85,
            issues=[],
            metrics={"word_count": 500}
        )
        response = client.post("/api/notes/test/hygiene")
        assert response.status_code == 200
        assert response.json()["data"]["health_score"] == 85

    def test_returns_issues(self, client, mock_service):
        mock_service.run_hygiene.return_value = HygieneResult(
            note_id="test",
            health_score=60,
            issues=[
                HygieneIssue(type="broken_link", severity="medium", detail="[[Missing]]")
            ],
            metrics={}
        )
        response = client.post("/api/notes/test/hygiene")
        assert len(response.json()["data"]["issues"]) == 1

    def test_applies_auto_fix(self, client, mock_service):
        response = client.post("/api/notes/test/hygiene?auto_fix=true")
        mock_service.run_hygiene.assert_called_with("test", auto_fix=True)
```

---

## Point 8 : Workflow Bouton SM-2 🔄

**Déjà implémenté et fonctionnel.** Aucune modification requise.

---

## Point 9 : Bouton Créer Nouvelle Note ➕

### Backend

```python
# src/frontin/api/models/notes.py
class CreateNoteRequest(BaseModel):
    """Request body for POST /notes."""
    title: str = Field(..., min_length=1, max_length=200)
    folder: str = Field(default="Personal Knowledge Management")
    content: Optional[str] = None


# src/frontin/api/routers/notes.py
@router.post("/", response_model=APIResponse[NoteResponse])
async def create_note(
    request: Request,
    data: CreateNoteRequest,
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[NoteResponse]:
    """
    Crée une nouvelle note dans le dossier spécifié.

    Si content est vide, utilise un template minimal : `# {title}`.
    """
    correlation_id = request.headers.get("X-Correlation-ID", "unknown")

    try:
        note = await service.create_note(
            title=data.title,
            folder=data.folder,
            content=data.content or f"# {data.title}\n\n",
        )
        logger.info(
            f"Note created: {note.note_id}",
            extra={"correlation_id": correlation_id, "note_id": note.note_id}
        )
        return APIResponse(success=True, data=note)
    except ScapinError as e:
        logger.error(f"Failed to create note: {e}", extra={"correlation_id": correlation_id})
        raise HTTPException(status_code=400, detail=e.message) from e
```

### Frontend - Modal Création

```svelte
<!-- web/src/lib/components/notes/CreateNoteModal.svelte -->
<script lang="ts">
    import { createNote } from '$lib/api/notes';
    import { goto } from '$app/navigation';

    interface Props {
        open: boolean;
        folder?: string;
        onclose: () => void;
    }

    let { open, folder = 'Personal Knowledge Management', onclose }: Props = $props();

    let title = $state('');
    let creating = $state(false);
    let error = $state<string | null>(null);

    async function handleSubmit() {
        if (!title.trim()) return;

        creating = true;
        error = null;

        try {
            const note = await createNote({ title: title.trim(), folder });
            onclose();
            goto(`/memoires/${encodeURIComponent(note.note_id)}`);
        } catch (e) {
            error = e instanceof Error ? e.message : 'Erreur';
        } finally {
            creating = false;
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') onclose();
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            handleSubmit();
        }
    }
</script>

{#if open}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div
        class="modal-backdrop"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-note-title"
        onkeydown={handleKeydown}
    >
        <div class="glass glass-solid rounded-2xl p-6 w-96" data-testid="create-note-modal">
            <h2 id="create-note-title" class="text-xl font-semibold mb-4">
                Nouvelle note
            </h2>

            {#if error}
                <div class="text-red-500 mb-4" role="alert">{error}</div>
            {/if}

            <label class="block mb-4">
                <span class="text-sm" style="color: var(--color-text-secondary);">Titre</span>
                <input
                    type="text"
                    bind:value={title}
                    class="glass-input w-full mt-1"
                    placeholder="Titre de la note"
                    autofocus
                    data-testid="create-note-title-input"
                />
            </label>

            <p class="text-sm mb-4" style="color: var(--color-text-tertiary);">
                📁 {folder}
            </p>

            <div class="flex justify-end gap-2">
                <button
                    onclick={onclose}
                    class="glass glass-interactive px-4 py-2 rounded-lg"
                    data-testid="create-note-cancel"
                >
                    Annuler
                </button>
                <button
                    onclick={handleSubmit}
                    disabled={!title.trim() || creating}
                    class="glass glass-interactive px-4 py-2 rounded-lg bg-blue-500 text-white"
                    data-testid="create-note-submit"
                >
                    {creating ? 'Création...' : 'Créer'}
                </button>
            </div>
        </div>
    </div>
{/if}
```

### Tests

```typescript
// web/e2e/pages/memoires.spec.ts
test.describe('Create Note', () => {
    test('can create a new note', async ({ page }) => {
        await page.goto('/memoires');

        // Ouvrir le modal
        await page.click('[data-testid="create-note-button"]');
        await expect(page.locator('[data-testid="create-note-modal"]')).toBeVisible();

        // Remplir le titre
        await page.fill('[data-testid="create-note-title-input"]', 'Ma Nouvelle Note');

        // Soumettre
        await page.click('[data-testid="create-note-submit"]');

        // Vérifier la redirection
        await page.waitForURL(/\/memoires\/.+/);
        await expect(page.locator('h1')).toContainText('Ma Nouvelle Note');
    });

    test('modal closes on Escape', async ({ page }) => {
        await page.goto('/memoires');
        await page.click('[data-testid="create-note-button"]');

        await page.keyboard.press('Escape');
        await expect(page.locator('[data-testid="create-note-modal"]')).not.toBeVisible();
    });

    test('validates empty title', async ({ page }) => {
        await page.goto('/memoires');
        await page.click('[data-testid="create-note-button"]');

        const submitButton = page.locator('[data-testid="create-note-submit"]');
        await expect(submitButton).toBeDisabled();
    });
});
```

---

## Point 10 : Activer NoteEnricher (Recherche Web) 🌐

### État Actuel
- `NoteEnricher` existe mais n'est jamais appelé (code mort)
- Champ `web_search_enabled` existe dans `NoteMetadata`

### Backend

```python
# src/frontin/api/models/notes.py
class EnrichmentSuggestion(BaseModel):
    """Une suggestion d'enrichissement."""
    source: str  # 'cross_reference', 'web_search', 'ai_analysis'
    title: str
    content: str
    confidence: float
    url: Optional[str] = None

class EnrichmentResult(BaseModel):
    """Résultat d'un enrichissement."""
    note_id: str
    suggestions: list[EnrichmentSuggestion]
    sources_used: list[str]


# src/frontin/api/routers/notes.py
@router.post("/{note_id}/enrich", response_model=APIResponse[EnrichmentResult])
async def enrich_note(
    request: Request,
    note_id: str,
    sources: list[str] = Query(default=["cross_reference"]),
    service: NotesService = Depends(get_notes_service),
) -> APIResponse[EnrichmentResult]:
    """
    Enrichit une note avec des sources externes.

    Sources disponibles:
    - cross_reference: Notes liées dans PKM (toujours disponible)
    - ai_analysis: Gap analysis IA (si auto_enrich=true)
    - web_search: Recherche Tavily (si web_search_enabled=true)
    """
    correlation_id = request.headers.get("X-Correlation-ID", "unknown")

    try:
        result = await service.enrich_note(note_id, sources)
        logger.info(
            f"Enrichment completed for {note_id}",
            extra={
                "correlation_id": correlation_id,
                "note_id": note_id,
                "sources": sources,
                "suggestions_count": len(result.suggestions)
            }
        )
        return APIResponse(success=True, data=result)
    except ScapinError as e:
        logger.error(f"Enrichment failed: {e}", extra={"correlation_id": correlation_id})
        raise HTTPException(status_code=400, detail=e.message) from e
```

### Service Layer

```python
# src/frontin/api/services/notes_service.py
async def enrich_note(self, note_id: str, sources: list[str]) -> EnrichmentResult:
    """Active NoteEnricher sur une note."""
    note = self.note_manager.get_note(note_id)
    if not note:
        raise ScapinError(f"Note not found: {note_id}")

    metadata = self.metadata_store.get(note_id)

    # Vérifier les permissions pour web_search
    if "web_search" in sources and not metadata.web_search_enabled:
        sources = [s for s in sources if s != "web_search"]
        logger.info(f"web_search disabled for note {note_id}, skipping")

    from src.passepartout.note_enricher import NoteEnricher

    enricher = NoteEnricher(
        ai_router=self.ai_router,
        note_manager=self.note_manager,
    )

    return await enricher.enrich(
        note=note,
        metadata=metadata,
        sources=sources,
    )
```

### Frontend

```svelte
<!-- web/src/lib/components/notes/EnrichButton.svelte -->
<script lang="ts">
    import { enrichNote } from '$lib/api/notes';
    import type { EnrichmentResult } from '$lib/api/types/notes';

    interface Props {
        noteId: string;
        webSearchEnabled?: boolean;
        onresult?: (result: EnrichmentResult) => void;
    }

    let { noteId, webSearchEnabled = false, onresult }: Props = $props();

    let loading = $state(false);
    let result = $state<EnrichmentResult | null>(null);

    async function handleEnrich() {
        loading = true;

        const sources = webSearchEnabled
            ? ['cross_reference', 'web_search']
            : ['cross_reference'];

        try {
            result = await enrichNote(noteId, sources);
            onresult?.(result);
        } finally {
            loading = false;
        }
    }
</script>

<button
    onclick={handleEnrich}
    disabled={loading}
    class="glass glass-interactive rounded-lg px-4 py-2"
    data-testid="enrich-button"
>
    {#if loading}
        <span class="spinner" />
    {:else}
        🌐 Enrichir
    {/if}
</button>

{#if result && result.suggestions.length > 0}
    <div class="glass glass-subtle rounded-lg p-4 mt-4" data-testid="enrich-result">
        <h4 class="font-medium mb-2">{result.suggestions.length} suggestions</h4>
        {#each result.suggestions as suggestion}
            <div class="border-b last:border-0 py-2" data-testid="enrich-suggestion">
                <span class="text-xs px-2 py-1 rounded bg-gray-100">
                    {suggestion.source}
                </span>
                <p class="font-medium">{suggestion.title}</p>
                <p class="text-sm" style="color: var(--color-text-secondary);">
                    {suggestion.content.slice(0, 150)}...
                </p>
            </div>
        {/each}
    </div>
{:else if result}
    <p class="text-sm mt-2" style="color: var(--color-text-tertiary);">
        Aucun enrichissement trouvé
    </p>
{/if}
```

### Tests

```python
class TestEnrichEndpoint:
    def test_enriches_with_cross_reference(self, client, mock_service):
        mock_service.enrich_note.return_value = EnrichmentResult(
            note_id="test",
            suggestions=[
                EnrichmentSuggestion(
                    source="cross_reference",
                    title="Note liée",
                    content="Contenu pertinent",
                    confidence=0.85
                )
            ],
            sources_used=["cross_reference"]
        )
        response = client.post("/api/notes/test/enrich?sources=cross_reference")
        assert response.status_code == 200
        assert len(response.json()["data"]["suggestions"]) == 1

    def test_respects_web_search_disabled(self, client, mock_service):
        """web_search ignoré si metadata.web_search_enabled=false."""
        response = client.post("/api/notes/test/enrich?sources=web_search")
        # Doit réussir mais sans utiliser web_search
        assert response.status_code == 200
```

---

## Ordre d'Implémentation

### Phase 0 : Migration (Prérequis)

| # | Commit | Validation |
|---|--------|------------|
| M1-M9 | Migration NoteReviewer | Voir section dédiée |

### Phase 1 : Améliorations

| Priorité | Point | Commit |
|----------|-------|--------|
| 1 | #2 | `feat(notes): afficher dossier dans vue détail` |
| 2 | #1 | `fix(search): ajouter seuil 40% et boost titre` |
| 3 | #4 | `feat(ui): ajouter tooltip facteur facilité SM-2` |
| 4 | #9 | `feat(notes): endpoint et UI création de note` |
| 5 | #6 | `feat(api): endpoint PATCH metadata` |
| 6 | #10 | `feat(notes): activer NoteEnricher` |
| 7 | #5 | `feat(notes): ajouter champ last_synced_at` |
| 8 | #7 | `feat(notes): endpoint et UI hygiène` |
| 9 | #3 | `feat(retouche): charger templates Modèle` |

---

## Checklist Bloquante (par commit)

```
□ Code implémenté et fonctionnel
□ Tests écrits et passants :
  - [ ] Test unitaire (backend)
  - [ ] Test E2E (UI)
  - [ ] Test cas d'erreur
□ npm run check : 0 erreur TypeScript
□ Ruff : 0 warning Python
□ Logs vérifiés : aucun ERROR/WARNING nouveau
□ Test manuel effectué — décrire ce qui a été vérifié
□ Documentation mise à jour (si applicable)
□ Pas de TODO, code commenté, ou console.log
□ data-testid sur tous les éléments interactifs
□ Commit atomique avec message descriptif
```

---

## Tests data-testid Référence

| Point | Element | data-testid |
|-------|---------|-------------|
| #1 | Champ recherche | `search-input` |
| #1 | Item résultat | `search-result-item` |
| #1 | Aucun résultat | `search-no-results` |
| #2 | Chemin dossier | `note-folder-path` |
| #4 | Badge EF | `easiness-factor` |
| #5 | Âge sync | `sync-age` |
| #6 | Éditeur metadata | `metadata-editor` |
| #6 | Select importance | `metadata-importance` |
| #6 | Select type | `metadata-note-type` |
| #6 | Checkbox auto-enrich | `metadata-auto-enrich` |
| #6 | Checkbox skip-revision | `metadata-skip-revision` |
| #6 | Checkbox web-search | `metadata-web-search` |
| #7 | Bouton hygiène | `hygiene-button` |
| #7 | Résultat hygiène | `hygiene-result` |
| #7 | Issue hygiène | `hygiene-issue` |
| #9 | Bouton créer | `create-note-button` |
| #9 | Modal création | `create-note-modal` |
| #9 | Input titre | `create-note-title-input` |
| #9 | Bouton annuler | `create-note-cancel` |
| #9 | Bouton soumettre | `create-note-submit` |
| #10 | Bouton enrichir | `enrich-button` |
| #10 | Résultat enrichissement | `enrich-result` |
| #10 | Suggestion | `enrich-suggestion` |

---

## Commandes de Validation

```bash
# TypeScript (0 erreur)
cd web && npm run check

# Ruff Python (0 warning)
ruff check src/

# Tests backend
pytest tests/passepartout/ tests/frontin/ -v

# Tests E2E
cd web && npx playwright test e2e/pages/memoires.spec.ts

# Logs
grep -E "(ERROR|WARNING)" data/logs/*.json | tail -20
```

---

## Documentation à Mettre à Jour

| Point | Fichier |
|-------|---------|
| #1 | `docs/user-guide/recherche.md` |
| #5 | `ARCHITECTURE.md` (schéma metadata) |
| #6 | `ARCHITECTURE.md` (API) |
| #7 | `docs/user-guide/notes.md` |
| #9 | `docs/user-guide/notes.md` |
| #10 | `docs/user-guide/notes.md` |
