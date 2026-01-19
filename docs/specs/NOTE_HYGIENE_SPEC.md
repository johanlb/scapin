# Note Hygiene Review — Specification v1.0

**Date** : 18 janvier 2026
**Statut** : Draft
**Auteur** : Johan + Claude

---

## Résumé Exécutif

La Revue Hygiène est un workflow IA qui analyse la cohérence et la qualité d'une note en la traitant comme un `PerceivedEvent` standard. Cette approche réutilise l'intégralité du pipeline cognitif existant (ContextEngine, Multi-Pass, Figaro) sans créer de nouveau workflow.

**Principe clé** : Une revue de note est un événement perçu comme les autres.

---

## Décision Architecturale

### ADR-001 : Note Review as PerceivedEvent

**Contexte** : Nous avons besoin d'un système de revue hygiène pour les notes qui :
- Trouve les notes liées (wikilinks + similarité sémantique)
- Détecte les incohérences et informations obsolètes
- Suggère des améliorations ou fusions
- Auto-applique certaines corrections (haute confiance)

**Décision** : Traiter la revue de note comme un `PerceivedEvent(source=note_review)` qui passe par le pipeline cognitif existant.

**Justification** :
1. **Réutilisation** : ContextEngine, Multi-Pass, Figaro sont déjà implémentés et testés
2. **Cohérence** : Même flux pour tous les types d'événements
3. **Escalade** : Bénéficie automatiquement de l'escalade Haiku → Sonnet → Opus
4. **Queue** : Les suggestions passent par la même queue de validation

**Conséquences** :
- Ajouter `EventType.NOTE_REVIEW` aux types d'événements
- Créer un template de prompt spécifique `note_review.j2`
- Ajouter des actions Figaro pour les opérations sur notes

---

## Architecture

### Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                    Sources d'Événements                         │
├─────────────┬─────────────┬─────────────┬─────────────────────┤
│   Email     │   Teams     │  Calendar   │   Note Review       │
│  (existant) │  (existant) │  (existant) │   (nouveau)         │
└──────┬──────┴──────┬──────┴──────┬──────┴──────────┬──────────┘
       │             │             │                  │
       ▼             ▼             ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PerceivedEvent                              │
│  • event_type: EMAIL | TEAMS | CALENDAR | NOTE_REVIEW           │
│  • source: email | teams | calendar | note_review               │
│  • content: contenu brut                                        │
│  • metadata: informations contextuelles                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Pipeline Cognitif (Trivelin)                  │
│                                                                 │
│  1. ContextEngine.retrieve_context()                            │
│     • Notes liées (wikilinks résolus)                          │
│     • Notes similaires (embeddings FAISS)                       │
│     • Sources croisées (Calendar, Teams si pertinent)           │
│                                                                 │
│  2. Multi-Pass Analysis (Sancho)                                │
│     • Pass 1: Extraction aveugle (Haiku)                        │
│     • Pass 2: Enrichissement contexte                           │
│     • Pass 3+: Raffinement si confiance < seuil                 │
│     • Escalade Sonnet/Opus si high-stakes                       │
│                                                                 │
│  3. Action Planning (Planchet)                                  │
│     • Évaluation risques                                        │
│     • Seuils auto-apply vs suggestion                           │
│                                                                 │
│  4. Execution (Figaro)                                          │
│     • Actions auto-appliquées (confiance ≥ 0.9)                 │
│     • Queue pour validation (confiance < 0.9)                   │
└─────────────────────────────────────────────────────────────────┘
```

### Flux Détaillé : Note Review

```
Utilisateur clique 🧹 sur une note
           │
           ▼
POST /api/notes/{id}/hygiene
           │
           ▼
┌─────────────────────────────────────────┐
│ Créer PerceivedEvent                    │
│                                         │
│ event_type: NOTE_REVIEW                 │
│ source: "note_review"                   │
│ content: note.content                   │
│ metadata:                               │
│   note_id: "xxx"                        │
│   title: "Marc Dupont"                  │
│   note_type: "personne"                 │
│   linked_notes: ["[[Acme Corp]]", ...]  │
│   current_frontmatter: {...}            │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ ContextEngine.retrieve_context()        │
│                                         │
│ Input: note content + title             │
│                                         │
│ Output:                                 │
│   • Wikilinks résolus (3 notes)         │
│   • Notes similaires FAISS (5 notes)    │
│   • Événements calendar liés (2)        │
│   • Messages Teams mentionnant (4)      │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ Sancho Multi-Pass (template: note_review.j2)
│                                         │
│ Analyse:                                │
│   • Cohérence interne                   │
│   • Contradictions avec notes liées     │
│   • Informations potentiellement obsolètes
│   • Liens cassés ([[Note inexistante]]) │
│   • Doublons potentiels                 │
│   • Champs manquants (frontmatter)      │
│   • Suggestions d'enrichissement        │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ Résultat: HygieneAnalysisResult         │
│                                         │
│ issues: [                               │
│   {type: "broken_link",                 │
│    detail: "[[Acme]] n'existe pas",     │
│    suggestion: "[[Acme Corp]]",         │
│    confidence: 0.95,                    │
│    auto_apply: true}                    │
│                                         │
│   {type: "potential_duplicate",         │
│    detail: "Similaire à 'M. Dupont'",   │
│    suggestion: "Fusionner les notes",   │
│    confidence: 0.72,                    │
│    auto_apply: false}                   │
│                                         │
│   {type: "missing_field",               │
│    detail: "Champ 'email' manquant",    │
│    suggestion: "marc@acme.com (trouvé   │
│                 dans email du 15/01)",  │
│    confidence: 0.88,                    │
│    auto_apply: false}                   │
│ ]                                       │
│                                         │
│ summary: "3 problèmes détectés,         │
│           1 corrigé automatiquement"    │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ Figaro: Exécution                       │
│                                         │
│ Auto-apply (confidence ≥ 0.9):          │
│   ✓ Lien [[Acme]] → [[Acme Corp]]       │
│                                         │
│ Queue pour validation:                  │
│   → Fusion avec 'M. Dupont'             │
│   → Ajout email marc@acme.com           │
└─────────────────────────────────────────┘
           │
           ▼
Notification utilisateur + UI mise à jour
```

---

## Composants à Implémenter

### Nouveaux Composants

| Composant | Fichier | Description |
|-----------|---------|-------------|
| `EventType.NOTE_REVIEW` | `src/core/events/universal_event.py` | Nouveau type d'événement |
| Template `note_review.j2` | `templates/ai/v2/note_review.j2` | Prompt d'analyse hygiène |
| `HygieneIssue` | `src/core/models/v2_models.py` | Modèle pour les problèmes détectés |
| `HygieneAnalysisResult` | `src/core/models/v2_models.py` | Résultat complet de l'analyse |
| Actions Figaro | `src/figaro/actions/notes.py` | `fix_link`, `merge_notes`, `update_field` |
| API Endpoint | `src/frontin/api/routers/notes.py` | `POST /api/notes/{id}/hygiene` |
| UI Button | `web/src/routes/notes/+page.svelte` | Bouton 🧹 + affichage résultats |

### Composants Réutilisés (sans modification)

| Composant | Fichier | Usage |
|-----------|---------|-------|
| `ContextEngine` | `src/passepartout/context_engine.py` | Récupération contexte |
| `EmbeddingGenerator` | `src/passepartout/embeddings.py` | Similarité sémantique |
| `CrossSourceEngine` | `src/passepartout/cross_source/` | Recherche multi-sources |
| `ReasoningEngine` | `src/sancho/reasoning_engine.py` | Analyse multi-pass |
| `CognitivePipeline` | `src/trivelin/cognitive_pipeline.py` | Orchestration |
| Queue Service | `src/frontin/api/services/queue_service.py` | Suggestions à valider |

---

## Types de Problèmes Détectés

| Type | Description | Auto-apply possible |
|------|-------------|---------------------|
| `broken_link` | Wikilink vers note inexistante | ✅ Si match unique trouvé |
| `potential_duplicate` | Note très similaire existe | ❌ Toujours manuel |
| `missing_field` | Champ frontmatter manquant | ✅ Si source fiable |
| `outdated_info` | Information potentiellement obsolète | ❌ Toujours manuel |
| `inconsistency` | Contradiction avec note liée | ❌ Toujours manuel |
| `orphan_note` | Note sans liens entrants/sortants | ❌ Information only |
| `suggested_link` | Devrait être liée à autre note | ✅ Si confiance ≥ 0.9 |

---

## Seuils de Confiance

| Action | Seuil Auto-Apply | Seuil Suggestion | En-dessous |
|--------|------------------|------------------|------------|
| Fix broken link | ≥ 0.95 | ≥ 0.7 | Ignoré |
| Add suggested link | ≥ 0.9 | ≥ 0.6 | Ignoré |
| Update field | ≥ 0.9 | ≥ 0.7 | Ignoré |
| Merge notes | — | ≥ 0.8 | Ignoré |
| Flag outdated | — | ≥ 0.6 | Ignoré |

---

## API

### Lancer une revue hygiène

```http
POST /api/notes/{note_id}/hygiene
Content-Type: application/json

{
  "include_cross_source": true,  // Chercher dans Calendar, Teams...
  "auto_apply": true,            // Appliquer corrections haute confiance
  "max_related_notes": 10        // Limite notes similaires à analyser
}
```

### Réponse

```json
{
  "success": true,
  "data": {
    "note_id": "marc-dupont",
    "analyzed_at": "2026-01-18T14:30:00Z",
    "duration_ms": 2340,
    "model_used": "claude-3-5-haiku",
    "context_notes_count": 8,
    "issues": [
      {
        "type": "broken_link",
        "severity": "warning",
        "detail": "Lien [[Acme]] pointe vers note inexistante",
        "suggestion": "Remplacer par [[Acme Corp]]",
        "confidence": 0.95,
        "auto_applied": true,
        "source": "fuzzy_match"
      },
      {
        "type": "potential_duplicate",
        "severity": "info",
        "detail": "Note très similaire: 'M. Dupont (Acme)'",
        "suggestion": "Envisager fusion des deux notes",
        "confidence": 0.72,
        "auto_applied": false,
        "related_note_id": "m-dupont-acme"
      }
    ],
    "summary": {
      "total_issues": 2,
      "auto_fixed": 1,
      "pending_review": 1,
      "health_score": 0.85
    }
  }
}
```

---

## UI/UX

### Bouton Hygiène

Position : Header de la note, à côté des boutons existants (✏️ 🗑️ 🔄 ↗️)

```
┌─────────────────────────────────────────────────────────────┐
│  Marc Dupont                          ✏️ 🗑️ 🧹 🔄 ↗️       │
│                                           ▲                 │
│                                     Bouton Hygiène          │
└─────────────────────────────────────────────────────────────┘
```

### États du bouton

| État | Icône | Comportement |
|------|-------|--------------|
| Idle | 🧹 | Clic lance l'analyse |
| Loading | ⟳ (spin) | Analyse en cours |
| Issues found | 🧹 + badge rouge | Affiche nombre de problèmes |
| Clean | ✨ | Note sans problème détecté |

### Panneau Résultats

Après analyse, afficher un panneau dépliable sous les métadonnées :

```
┌─────────────────────────────────────────────────────────────┐
│ 🧹 Revue Hygiène                              Score: 85%   │
├─────────────────────────────────────────────────────────────┤
│ ✅ Lien corrigé: [[Acme]] → [[Acme Corp]]                  │
│                                                             │
│ ⚠️ Doublon potentiel avec "M. Dupont (Acme)"               │
│    [Voir] [Fusionner] [Ignorer]                            │
│                                                             │
│ ℹ️ Champ 'email' manquant                                   │
│    Suggestion: marc@acme.com (source: email 15/01)         │
│    [Appliquer] [Ignorer]                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Template IA : note_review.j2

```jinja2
Tu es un assistant qui analyse la cohérence et la qualité des notes de connaissance.

## Note à Analyser

**Titre** : {{ note.title }}
**Type** : {{ note.type }}
**Contenu** :
{{ note.content }}

**Frontmatter actuel** :
{{ note.frontmatter | tojson(indent=2) }}

## Notes Liées (wikilinks)
{% for linked in context.linked_notes %}
### {{ linked.title }}
{{ linked.excerpt }}
{% endfor %}

## Notes Similaires (recherche sémantique)
{% for similar in context.similar_notes %}
### {{ similar.title }} (score: {{ similar.relevance }})
{{ similar.excerpt }}
{% endfor %}

## Analyse Demandée

Analyse cette note et identifie :

1. **Liens cassés** : Wikilinks vers notes inexistantes
   - Suggère une correction si une note similaire existe

2. **Doublons potentiels** : Notes très similaires qui pourraient être fusionnées
   - Indique le niveau de similarité

3. **Incohérences** : Contradictions avec les notes liées
   - Cite les passages contradictoires

4. **Informations obsolètes** : Données potentiellement périmées
   - Indique pourquoi tu penses qu'elles sont obsolètes

5. **Champs manquants** : Frontmatter incomplet pour ce type de note
   - Suggère des valeurs si trouvées dans le contexte

6. **Liens suggérés** : Notes qui devraient être liées
   - Explique pourquoi le lien serait pertinent

## Format de Réponse

```json
{
  "issues": [
    {
      "type": "broken_link|potential_duplicate|inconsistency|outdated_info|missing_field|suggested_link",
      "severity": "error|warning|info",
      "location": "ligne ou section concernée",
      "detail": "description du problème",
      "suggestion": "correction proposée",
      "confidence": 0.0-1.0,
      "source": "comment tu as trouvé cette information"
    }
  ],
  "health_score": 0.0-1.0,
  "summary": "résumé en une phrase"
}
```
```

---

## Estimation d'Implémentation

| Phase | Composants | Lignes estimées |
|-------|------------|-----------------|
| 1 | EventType + Models | ~100 |
| 2 | Template note_review.j2 | ~150 |
| 3 | Actions Figaro (fix_link, update_field) | ~200 |
| 4 | API Endpoint + Service | ~250 |
| 5 | UI (bouton + panneau résultats) | ~300 |
| **Total** | | **~1000 lignes** |

---

## Liens avec Autres Features

### Recherche API (à implémenter)

La recherche API utilise le même `ContextEngine` :

```python
# Recherche notes
results = await context_engine.retrieve_context(
    query=search_query,
    top_k=20,
    min_relevance=0.3
)
```

### Visualisation Media (à implémenter)

Les media sont indépendants mais peuvent être référencés dans les issues :

```json
{
  "type": "missing_media",
  "detail": "Image référencée mais fichier introuvable",
  "suggestion": "Resynchroniser depuis Apple Notes"
}
```

---

## Changelog

| Version | Date | Changements |
|---------|------|-------------|
| 1.0 | 2026-01-18 | Draft initial |
