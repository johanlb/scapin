# Système de Paths des Notes - Documentation Technique

## Vue d'ensemble

Ce document décrit le fonctionnement du système de paths des notes dans Scapin.

## Concepts clés

| Champ | Description | Exemple |
|-------|-------------|---------|
| `note_id` | Identifiant unique invariant (slug + hash) | `reunion-abc-7f8e9d0a` |
| `path` | Dossier parent seulement (sans le note_id) | `Clients/ABC` ou `""` (racine) |
| URL complète | `/memoires/{path}/{note_id}` | `/memoires/Clients/ABC/reunion-abc-7f8e9d0a` |

## Structure de stockage (Backend)

```
~/Documents/Scapin/Notes/
├── note-at-root-123abc.md          # Note à la racine (path = "")
├── Clients/
│   └── ABC/
│       └── reunion-abc-7f8e9d0a.md  # Note dans dossier (path = "Clients/ABC")
└── Personnes/
    └── jean-dupont-xyz789.md        # Note dans dossier (path = "Personnes")
```

### Mapping fichier → champs

```
Chemin physique: ~/Documents/Scapin/Notes/Clients/ABC/reunion-abc-7f8e9d0a.md

Décomposition:
├── notes_dir     : ~/Documents/Scapin/Notes/
├── path          : Clients/ABC         (dossier parent relatif)
├── note_id       : reunion-abc-7f8e9d0a (nom du fichier sans .md)
└── extension     : .md
```

## Génération du note_id

Le `note_id` est généré **une seule fois** à la création et ne change JAMAIS :

```python
def _generate_note_id(title: str, timestamp: str) -> str:
    # 1. Nettoie le titre
    safe_title = sanitize_title(title)

    # 2. Crée un slug : "Réunion ABC" → "reunion-abc"
    slug = re.sub(r"[^a-z0-9]+", safe_title.lower())[:50]

    # 3. Ajoute un hash SHA256 pour l'unicité
    hash_suffix = sha256(f"{title}{timestamp}")[:8]

    # Résultat: "reunion-abc-7f8e9d0a"
    return f"{slug}-{hash_suffix}"
```

## Réponse API (NoteResponse)

```json
{
  "note_id": "reunion-abc-7f8e9d0a",
  "title": "Réunion ABC - Q1 2026",
  "path": "Clients/ABC",
  "content": "# Contenu...",
  "excerpt": "Discussion de la phase 2...",
  "tags": ["clients", "reunion"],
  "created_at": "2026-01-21T10:30:00Z",
  "updated_at": "2026-01-21T14:45:00Z",
  "pinned": false
}
```

## Navigation Frontend

### Route dynamique

La route `/memoires/[...path]/+page.svelte` utilise un paramètre catch-all :

```svelte
const notePath = $derived($page.params.path);          // "Clients/ABC/reunion-abc-7f8e9d0a"
const pathParts = $derived(notePath.split('/'));       // ["Clients", "ABC", "reunion-abc-7f8e9d0a"]
const noteId = $derived(pathParts[pathParts.length-1]); // "reunion-abc-7f8e9d0a"
```

### Construction d'URLs (PATTERN CORRECT)

```typescript
function buildNoteUrl(note: { note_id: string; path: string }): string {
  const fullPath = note.path
    ? `${note.path}/${note.note_id}`
    : note.note_id;
  return `/memoires/${fullPath}`;
}
```

### Exemples

| path | note_id | URL résultante |
|------|---------|----------------|
| `""` | `meeting-123` | `/memoires/meeting-123` |
| `Clients` | `abc-456` | `/memoires/Clients/abc-456` |
| `Clients/ABC` | `reunion-789` | `/memoires/Clients/ABC/reunion-789` |

## Comportement lors du déplacement

Quand une note est déplacée vers un autre dossier :

- `note_id` : **RESTE INCHANGÉ** (identifiant permanent)
- `path` : **CHANGE** (nouveau dossier parent)
- URL : **CHANGE** (car inclut le path)

```
Avant: /memoires/Clients/ABC/reunion-abc-7f8e9d0a
Après: /memoires/Projets/reunion-abc-7f8e9d0a
```

## Points importants

1. **Le note_id suffit pour l'API** : `GET /api/notes/{note_id}` trouve la note quel que soit son dossier

2. **Le path est optionnel dans l'URL** : `/memoires/{note_id}` fonctionne (path = [note_id])

3. **Pas d'encodage du path entier** : Les `/` sont préservés dans l'URL

4. **Wikilinks** : Utilisent `/memoires/{text_du_wikilink}` (sans path car inconnu)

## Erreurs courantes à éviter

| Erreur | Correct |
|--------|---------|
| `/notes/{note_id}` | `/memoires/{note_id}` |
| `/memoires/{path}` (sans note_id) | `/memoires/{path}/{note_id}` |
| `encodeURIComponent(fullPath)` | Pas d'encodage global (préserver les `/`) |

## Fichiers concernés

### Routes
- `web/src/routes/memoires/[...path]/+page.svelte` - Page détail note
- `web/src/routes/memoires/+page.svelte` - Liste des notes

### Navigation
- `web/src/lib/utils/markdown.ts` - Wikilinks
- `web/src/lib/components/ui/CommandPalette.svelte` - Recherche globale
- `web/src/routes/memoires/review/+page.svelte` - Révision SM-2
- `web/src/routes/memoires/filage/+page.svelte` - Briefing matinal

### API
- `src/frontin/api/models/notes.py` - Modèles Pydantic
- `src/frontin/api/services/notes_service.py` - Service notes
- `src/passepartout/note_manager.py` - Gestionnaire fichiers
