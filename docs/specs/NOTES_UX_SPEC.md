# Notes UX Improvements — Specification v1.0

**Date** : 18 janvier 2026
**Statut** : Draft
**Auteur** : Johan + Claude

---

## Résumé

Ce document spécifie les améliorations UX pour la page Notes :
1. **Recherche API** — Recherche full-text dans le contenu des notes
2. **Visualisation Media** — Affichage des images, PDFs et audio intégrés
3. **Édition titre inline** — Modification du titre sans éditer tout le contenu
4. **Revue Hygiène** — Voir [NOTE_HYGIENE_SPEC.md](NOTE_HYGIENE_SPEC.md)

---

## 1. Recherche API

### Objectif

Permettre une recherche puissante dans toutes les notes, pas seulement un filtrage local.

### Backend

#### Endpoint

```http
GET /api/notes/search?q={query}&limit={limit}&offset={offset}
```

#### Paramètres

| Param | Type | Défaut | Description |
|-------|------|--------|-------------|
| `q` | string | required | Requête de recherche |
| `limit` | int | 20 | Nombre max de résultats |
| `offset` | int | 0 | Pagination |
| `folder` | string | null | Filtrer par dossier |
| `type` | string | null | Filtrer par type (personne, projet...) |

#### Réponse

```json
{
  "success": true,
  "data": {
    "query": "marc budget",
    "total": 42,
    "results": [
      {
        "note_id": "marc-dupont",
        "title": "Marc Dupont",
        "excerpt": "...discussion sur le **budget** Q2...",
        "score": 0.92,
        "highlights": [
          {"field": "content", "snippet": "Marc a confirmé le **budget**..."}
        ],
        "folder": "Personnes",
        "updated_at": "2026-01-15T10:00:00Z"
      }
    ]
  }
}
```

#### Implémentation

```python
# src/jeeves/api/routers/notes.py

@router.get("/search")
async def search_notes(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    folder: Optional[str] = None,
    note_type: Optional[str] = None,
    notes_service: NotesService = Depends(get_notes_service),
) -> APIResponse:
    """Search notes using full-text and semantic search."""
    results = await notes_service.search(
        query=q,
        limit=limit,
        offset=offset,
        folder=folder,
        note_type=note_type,
    )
    return APIResponse(success=True, data=results)
```

```python
# src/jeeves/api/services/notes_service.py

async def search(
    self,
    query: str,
    limit: int = 20,
    offset: int = 0,
    folder: Optional[str] = None,
    note_type: Optional[str] = None,
) -> dict:
    """
    Search notes using hybrid approach:
    1. Full-text search in title and content
    2. Semantic search via ContextEngine
    3. Merge and rank results
    """
    # Use ContextEngine for semantic search
    context_results = await self.context_engine.retrieve_context(
        query=query,
        top_k=limit * 2,  # Get more for merging
        min_relevance=0.3,
    )

    # Also do simple text matching for exact matches
    text_matches = self.note_manager.search_text(query)

    # Merge, dedupe, and rank
    merged = self._merge_search_results(context_results, text_matches)

    # Apply filters
    if folder:
        merged = [r for r in merged if r.folder == folder]
    if note_type:
        merged = [r for r in merged if r.note_type == note_type]

    # Paginate
    total = len(merged)
    results = merged[offset:offset + limit]

    return {
        "query": query,
        "total": total,
        "results": [self._format_search_result(r) for r in results],
    }
```

### Frontend

#### UI : Barre de recherche

Position : Au-dessus de la liste des notes (colonne 2)

```
┌─────────────────────────────────────────────────────┐
│  🔍 Rechercher...                          [Cmd+K] │
├─────────────────────────────────────────────────────┤
│  Aujourd'hui                                        │
│    • Marc Dupont                                    │
│    • Projet Alpha                                   │
│  ...                                                │
└─────────────────────────────────────────────────────┘
```

#### Comportement

| Action | Comportement |
|--------|--------------|
| Focus | `Cmd+K` ou clic |
| Typing | Debounce 300ms, puis appel API |
| Résultats | Remplace la liste des notes |
| Clear | `Esc` ou bouton ✕, retour à la liste normale |
| Sélection | Clic ou flèches + Enter |

#### Highlights

Les termes recherchés sont mis en surbrillance dans les résultats :
- Titre : `<mark>` autour des matches
- Excerpt : `**bold**` autour des matches

---

## 2. Visualisation Media

### Objectif

Afficher les pièces jointes des notes Apple Notes (images, PDFs, audio).

### Architecture

```
Apple Notes
    │
    ▼
~/Library/Group Containers/group.com.apple.notes/
    ├── NoteStore.sqlite (métadonnées)
    └── Media/
        └── {uuid}/
            ├── image.jpg
            ├── document.pdf
            └── audio.m4a
```

### Backend

#### Endpoint

```http
GET /api/media/{attachment_id}
```

#### Headers de réponse

```
Content-Type: image/jpeg | application/pdf | audio/mp4
Content-Disposition: inline; filename="image.jpg"
Cache-Control: max-age=86400
```

#### Implémentation

```python
# src/jeeves/api/routers/media.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter(prefix="/api/media", tags=["media"])

APPLE_NOTES_MEDIA = Path.home() / "Library/Group Containers/group.com.apple.notes/Media"

MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".pdf": "application/pdf",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
}

@router.get("/{attachment_id}")
async def get_media(attachment_id: str) -> FileResponse:
    """Serve media file from Apple Notes."""
    # Security: validate attachment_id format (UUID)
    if not is_valid_uuid(attachment_id):
        raise HTTPException(400, "Invalid attachment ID")

    # Find file in media directory
    media_dir = APPLE_NOTES_MEDIA / attachment_id
    if not media_dir.exists():
        raise HTTPException(404, "Media not found")

    # Find the actual file (could be any extension)
    files = list(media_dir.glob("*"))
    if not files:
        raise HTTPException(404, "Media file not found")

    file_path = files[0]  # Usually only one file per attachment
    mime_type = MIME_TYPES.get(file_path.suffix.lower(), "application/octet-stream")

    return FileResponse(
        file_path,
        media_type=mime_type,
        headers={"Cache-Control": "max-age=86400"},
    )
```

#### Service de parsing des attachments

```python
# src/integrations/apple/notes_client.py

def get_note_attachments(self, note_id: str) -> list[dict]:
    """Get attachments for a note from Apple Notes database."""
    # Query NoteStore.sqlite for attachments
    # Return list of {id, type, filename, size}
    pass
```

### Frontend

#### Markdown Extension

Ajouter le support des références media dans le rendu Markdown :

```typescript
// web/src/lib/utils/markdown.ts

// Extension for Apple Notes media references
const mediaExtension: TokenizerExtension & RendererExtension = {
  name: 'applemedia',
  level: 'inline',

  start(src: string): number | undefined {
    return src.indexOf('![');
  },

  tokenizer(src: string): MediaToken | undefined {
    // Match: ![alt](apple-media://attachment-id)
    const match = /^!\[([^\]]*)\]\(apple-media:\/\/([a-f0-9-]+)\)/.exec(src);
    if (match) {
      return {
        type: 'applemedia',
        raw: match[0],
        alt: match[1],
        attachmentId: match[2],
      };
    }
  },

  renderer(token: MediaToken): string {
    const { alt, attachmentId } = token;
    // Determine type from context or fetch
    return `<img src="/api/media/${attachmentId}" alt="${alt}" loading="lazy" />`;
  },
};
```

#### Composants Media

```svelte
<!-- web/src/lib/components/notes/MediaViewer.svelte -->

<script lang="ts">
  interface Props {
    attachmentId: string;
    type: 'image' | 'pdf' | 'audio';
    alt?: string;
  }

  let { attachmentId, type, alt = '' }: Props = $props();

  const src = `/api/media/${attachmentId}`;
</script>

{#if type === 'image'}
  <img {src} {alt} loading="lazy" class="rounded-lg max-w-full" />
{:else if type === 'pdf'}
  <iframe
    {src}
    title={alt}
    class="w-full h-96 rounded-lg border"
  />
{:else if type === 'audio'}
  <audio controls class="w-full">
    <source {src} type="audio/mp4" />
    Votre navigateur ne supporte pas l'audio.
  </audio>
{/if}
```

#### Affichage dans la liste des attachments

Sous le contenu de la note, afficher les pièces jointes :

```
┌─────────────────────────────────────────────────────┐
│  [Contenu de la note en Markdown]                   │
│                                                     │
├─────────────────────────────────────────────────────┤
│  📎 Pièces jointes (3)                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐               │
│  │  [img]  │ │  [PDF]  │ │  [🎵]   │               │
│  │ photo   │ │ doc.pdf │ │ audio   │               │
│  └─────────┘ └─────────┘ └─────────┘               │
└─────────────────────────────────────────────────────┘
```

---

## 3. Édition Titre Inline

### Objectif

Permettre de modifier le titre de la note sans entrer en mode édition complet.

### UI

#### État normal

```
┌─────────────────────────────────────────────────────┐
│  Marc Dupont                          ✏️ 🗑️ 🧹 🔄 ↗️ │
│  ▲                                                   │
│  Double-clic pour éditer                            │
└─────────────────────────────────────────────────────┘
```

#### État édition

```
┌─────────────────────────────────────────────────────┐
│  ┌──────────────────────────────────┐  ✓  ✕        │
│  │ Marc Dupont█                     │               │
│  └──────────────────────────────────┘               │
└─────────────────────────────────────────────────────┘
```

### Comportement

| Action | Résultat |
|--------|----------|
| Double-clic sur titre | Passe en mode édition |
| Enter | Sauvegarde |
| Escape | Annule |
| Clic ailleurs | Sauvegarde |
| ✓ | Sauvegarde |
| ✕ | Annule |

### Implémentation Frontend

```svelte
<!-- Dans +page.svelte -->

<script lang="ts">
  let isEditingTitle = $state(false);
  let editedTitle = $state('');

  function startEditingTitle() {
    if (!selectedNote) return;
    editedTitle = selectedNote.title;
    isEditingTitle = true;
  }

  async function saveTitle() {
    if (!selectedNote || !editedTitle.trim()) return;

    try {
      await updateNote(selectedNote.note_id, { title: editedTitle.trim() });
      selectedNote.title = editedTitle.trim();
    } catch (error) {
      console.error('Failed to update title:', error);
    } finally {
      isEditingTitle = false;
    }
  }

  function cancelEditingTitle() {
    isEditingTitle = false;
    editedTitle = '';
  }
</script>

<!-- Title -->
{#if isEditingTitle}
  <div class="flex items-center gap-2">
    <input
      type="text"
      bind:value={editedTitle}
      onkeydown={(e) => {
        if (e.key === 'Enter') saveTitle();
        if (e.key === 'Escape') cancelEditingTitle();
      }}
      onblur={saveTitle}
      class="text-2xl font-bold bg-transparent border-b-2 border-amber-500 outline-none flex-1"
      autofocus
    />
    <button onclick={saveTitle} class="text-green-500">✓</button>
    <button onclick={cancelEditingTitle} class="text-red-500">✕</button>
  </div>
{:else}
  <h1
    class="text-2xl font-bold cursor-pointer hover:text-amber-600"
    ondblclick={startEditingTitle}
    title="Double-clic pour modifier"
  >
    {selectedNote.title}
  </h1>
{/if}
```

### Backend

L'endpoint `PATCH /api/notes/{id}` existe déjà et supporte la mise à jour du titre.

---

## 4. Raccourcis Clavier

| Raccourci | Action |
|-----------|--------|
| `Cmd+K` | Focus recherche |
| `Cmd+E` | Éditer note |
| `Cmd+S` | Sauvegarder (en mode édition) |
| `Escape` | Annuler édition / Fermer recherche |
| `↑` / `↓` | Naviguer dans la liste |
| `Enter` | Sélectionner note |

---

## Estimation

| Feature | Backend | Frontend | Total |
|---------|---------|----------|-------|
| Recherche API | ~150 lignes | ~100 lignes | ~250 |
| Media API | ~100 lignes | ~150 lignes | ~250 |
| Titre inline | — | ~50 lignes | ~50 |
| Raccourcis | — | ~30 lignes | ~30 |
| **Total** | **~250** | **~330** | **~580** |

---

## Ordre d'Implémentation Suggéré

1. **Recherche API** — Débloque l'UX principale
2. **Titre inline** — Quick win, amélioration immédiate
3. **Media API** — Plus complexe, nécessite parsing Apple Notes DB
4. **Raccourcis** — Polish final

---

## Changelog

| Version | Date | Changements |
|---------|------|-------------|
| 1.0 | 2026-01-18 | Draft initial |
