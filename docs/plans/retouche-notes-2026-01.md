# Plan : Retouche Fonctionnel

**Branche** : `hygiene-des-notes`
**Date** : Janvier 2026
**Objectif** : Système de Retouche IA complet pour l'hygiène des notes

---

## 1. Vision

### Qu'est-ce que la Retouche ?

La Retouche est le **cycle d'amélioration automatique** des notes par l'IA.
Elle maintient la base de connaissances à jour, structurée et interconnectée.

### Déclenchement

| Mode | Quand | Actions |
|------|-------|---------|
| **Automatique** | Selon calendrier SM-2 | Scoring + actions haute confiance |
| **Manuel** | Bouton UI | Preview → Validation → Application |

### Autonomie

| Confiance | Comportement |
|-----------|--------------|
| ≥ 85% | Application automatique |
| 70-84% | Proposition (attente validation) |
| < 70% | Escalade modèle (Haiku → Sonnet → Opus) |

---

## 2. Actions de Retouche

### 2.1 Actions par Objectif

| Action | Code | Description | Seuil auto |
|--------|------|-------------|------------|
| **Score** | `score` | Évaluer la qualité 0-100 | Toujours auto |
| **Structure** | `structure` | Réorganiser les sections | 85% |
| **Enrichir** | `enrich` | Compléter infos manquantes | 85% |
| **Questions** | `inject_questions` | Poser des questions stratégiques | 90% |
| **Liens** | `suggest_links` | Suggérer des wikilinks | 80% |
| **Nettoyer** | `cleanup` | Supprimer contenu obsolète | 90% |
| **Résumer** | `summarize` | Générer un résumé en-tête | 85% |
| **Refactorer** | `restructure_graph` | Proposer split/merge | 95% (jamais auto) |

### 2.2 Actions par Type de Note

#### PERSONNE (contacts)
```
Priorité : Structure > Enrichir > Liens > Questions
```
| Action | Détail |
|--------|--------|
| Structure | Sections : Infos, Historique, Notes, Projets |
| Enrichir | Compléter rôle, entreprise, contact |
| Liens | Suggérer [[Entreprise]], [[Projets communs]] |
| Questions | "Quand avez-vous échangé ?" "Projets en cours ?" |
| Nettoyer | Supprimer coordonnées obsolètes |

#### PROJET (initiatives)
```
Priorité : Structure > Nettoyer > Questions > Liens
```
| Action | Détail |
|--------|--------|
| Structure | Sections : Objectif, Parties prenantes, Timeline, Historique |
| Nettoyer | Archiver les infos des phases terminées |
| Questions | "Prochaine étape ?" "Blocages non documentés ?" |
| Liens | Suggérer [[Personnes]], [[Entités]], [[Réunions]] |
| Refactorer | Si projet trop gros → split en sous-projets |

#### ENTITÉ (organisations)
```
Priorité : Enrichir > Liens > Structure
```
| Action | Détail |
|--------|--------|
| Enrichir | Secteur, contacts, site web |
| Liens | Suggérer [[Contacts]], [[Projets]] |
| Structure | Sections : Présentation, Contacts, Projets |

#### RÉUNION (CR)
```
Priorité : Structure > Enrichir > Liens
```
| Action | Détail |
|--------|--------|
| Structure | Sections : Participants, Agenda, Décisions, Actions |
| Enrichir | Extraire actions non formalisées |
| Liens | Suggérer [[Participants]], [[Projet associé]] |
| Nettoyer | Archiver si > 6 mois et pas d'actions pending |

#### PROCESSUS (procédures)
```
Priorité : Structure > Nettoyer > Questions
```
| Action | Détail |
|--------|--------|
| Structure | Étapes numérotées, prérequis, checklist |
| Nettoyer | Supprimer étapes obsolètes |
| Questions | "Étapes manquantes ?" "Cas limites ?" |

#### SOUVENIR / ÉVÉNEMENT
```
Priorité : Aucune modification
```
- Auto-enrich : **DÉSACTIVÉ**
- Seul le scoring est autorisé

---

## 3. Amélioration du Contexte IA

### Objectif

Chaque Retouche doit enrichir le frontmatter pour aider les analyses futures.

### Champs à maintenir

| Champ | Usage |
|-------|-------|
| `aliases` | Noms alternatifs détectés |
| `tags` | Classification automatique |
| `related` | Wikilinks extraits du contenu |
| `last_activity` | Date dernière activité détectée |
| `pending_updates` | Propositions en attente de validation |

### Résumé contextuel

Chaque note PROJET et PERSONNE devrait avoir un **résumé en-tête** :

```markdown
> **Résumé** : [1-2 phrases décrivant l'essentiel pour le contexte IA]
```

Ce résumé est utilisé par Sancho lors des analyses d'emails/événements.

---

## 4. Déduplication et Refactoring

### Détection de doublons

L'IA compare les nouvelles notes avec l'existant :
- Similarité titre > 80% → alerte
- Contenu recoupant > 60% → suggestion merge

### Refactoring de domaine

Quand un PROJET devient trop gros :
1. Détecter les sous-thèmes distincts
2. Proposer un split avec structure :
   - Note parent (vue d'ensemble)
   - Notes enfants (sous-projets)
   - Maintien des liens bidirectionnels

**Confiance requise : 95%** (jamais auto, toujours proposition)

---

## 5. Architecture Technique

### Flux de données

```
Note due pour retouche
    │
    ▼
RetoucheReviewer.review_note()
    │
    ├── _load_context() → Note + frontmatter + liens
    │
    ├── _build_retouche_prompt() → Template Jinja2 par type
    │
    ├── _call_ai_router() → Claude (Haiku → Sonnet → Opus)
    │
    ├── _parse_ai_response() → Actions structurées
    │
    └── Pour chaque action :
            │
            ├── confiance ≥ 85% → _apply_action()
            │
            └── confiance < 85% → pending_updates[]
                    │
                    ▼
            UI: RetoucheDiff modal
```

### Problème actuel

`_call_ai_router()` dans `retouche_reviewer.py:475` est un **placeholder vide**.

---

## 6. Phases d'Implémentation

### Phase 0 : Refactoring Briques Communes ✅ PREMIÈRE ÉTAPE

**Objectif** : Extraire les briques partagées avant d'implémenter la Retouche

**Fichiers à créer** :
- `src/sancho/analysis_engine.py` — Classe abstraite + utilitaires

**Contenu de `analysis_engine.py`** :
```python
class AnalysisEngine(ABC):
    """Base class for AI-powered analysis"""

    # Escalade modèle partagée
    async def _call_with_escalation(
        self,
        prompt: str,
        initial_model: AIModel = AIModel.HAIKU,
        escalation_thresholds: dict = None
    ) -> tuple[dict, AIModel]:
        ...

    # Parsing JSON robuste
    def _parse_json_response(self, response: str) -> dict:
        ...

    # Gestion erreurs
    def _handle_ai_error(self, error: Exception) -> dict:
        ...

    # Méthodes abstraites
    @abstractmethod
    def _build_prompt(self, context: Any) -> str: ...

    @abstractmethod
    def _process_result(self, result: dict) -> Any: ...
```

**Fichiers à modifier** :
- `src/sancho/multi_pass_analyzer.py` — Hériter de `AnalysisEngine`
- `src/passepartout/retouche_reviewer.py` — Hériter de `AnalysisEngine`

**Validation** :
- Tests existants passent toujours
- Aucune régression sur l'analyse d'emails

---

### Phase 1 : Connexion IA (backend)

**Fichiers :**
- `src/passepartout/retouche_reviewer.py`

**Tâches :**
1. Implémenter `_call_ai_router()` avec AIRouter
2. Ajouter system prompt cacheable
3. Parser réponse JSON
4. Gérer escalade modèles

**Validation :**
- Test unitaire avec mock
- Test réel sur 1 note

---

### Phase 2 : Prompts Spécialisés (backend)

**Fichiers à créer :**
- `templates/ai/v2/retouche/base.j2`
- `templates/ai/v2/retouche/personne.j2`
- `templates/ai/v2/retouche/projet.j2`
- `templates/ai/v2/retouche/reunion.j2`
- `templates/ai/v2/retouche/entite.j2`
- `templates/ai/v2/retouche/processus.j2`

**Fichiers à modifier :**
- `src/passepartout/retouche_reviewer.py` — Utiliser templates
- `src/sancho/template_renderer.py` — Méthode `render_retouche()`

**Validation :**
- Chaque type génère un prompt adapté

---

### Phase 3 : Actions Avancées (backend)

**Nouvelles actions à implémenter :**
- `suggest_links` — Recherche sémantique notes liées
- `cleanup` — Détection contenu obsolète
- `profile_insight` — Profil psychologique
- `create_omnifocus` — Création tâche via Figaro

**Fichiers :**
- `src/passepartout/retouche_reviewer.py` — Méthodes `_apply_*`

**Validation :**
- Chaque action produit un diff cohérent

---

### Phase 4 : Preview UI (frontend)

**Fichiers à créer :**
- `web/src/lib/components/notes/RetoucheDiff.svelte`
- `web/src/lib/components/notes/RetoucheBadge.svelte`

**Fichiers à modifier :**
- `src/frontin/api/routers/briefing.py` — Endpoint preview
- `web/src/lib/api/client.ts` — Fonction `previewRetouche()`
- `web/src/routes/memoires/[...path]/+page.svelte` — Bouton

**Validation :**
- Modal affiche diff coloré
- Boutons Appliquer / Ignorer / Reporter

---

### Phase 5 : Queue UI + Rollback (frontend)

**Fichiers à créer :**
- `web/src/lib/components/notes/RetoucheQueue.svelte`

**Fichiers à modifier :**
- `src/frontin/api/routers/notes.py` — Endpoint rollback
- `web/src/lib/components/notes/RetoucheHistory.svelte` — Bouton annuler

**Validation :**
- Page affiche retouches en attente
- Rollback fonctionne

---

### Phase 6 : Tests et Documentation

**Fichiers :**
- `tests/unit/test_retouche_reviewer.py`
- `web/e2e/retouche.spec.ts`

**Validation :**
- 0 échec pytest
- 0 échec Playwright
- 0 warning Ruff/TypeScript

---

## 7. Fichiers Critiques

| Fichier | Rôle |
|---------|------|
| `src/passepartout/retouche_reviewer.py` | Moteur Retouche |
| `src/passepartout/note_types.py` | Config par type |
| `src/sancho/router.py` | Appels Claude |
| `src/sancho/template_renderer.py` | Rendu Jinja2 |
| `web/src/lib/components/notes/VersionDiff.svelte` | Composant diff |

---

## 8. Scheduling Détaillé

### Configuration Background Worker

```python
max_daily_retouches = 100      # Limite quotidienne
retouche_batch_size = 10       # Notes par batch
quiet_hours = 23h-7h           # Pause nocturne
filage_hour = 6h               # Préparation matinale
sleep_between_reviews = 10s    # Délai entre notes
```

### Cycle SM-2 pour Retouche

| Répétition | Intervalle | Description |
|------------|------------|-------------|
| 1ère | 2h | Premier passage |
| 2ème | 12h | Confirmation |
| 3ème+ | `I(n-1) × EF` | Espacement progressif |

**EF (Easiness Factor)** : 1.3 — 2.5 (ajusté selon qualité)

### Flux Quotidien

```
00:00  Reset stats quotidiens
06:00  Préparation Filage (lectures du jour)
07:00  Début retouches (batch de 10)
       ↓ 10 notes → pause 10s → 10 notes → ...
23:00  Fin retouches (quiet hours)
```

### Priorisation des Notes

1. Notes avec `retouche_next < now()`
2. Notes jamais retouchées (`retouche_count = 0`)
3. Notes avec `quality_score < 50`

---

## 9. Prompts Détaillés

### System Prompt (cacheable)

```
Tu es Scapin, l'assistant cognitif de Johan.

Mission : Améliorer la qualité des notes de sa base de connaissances personnelle.

## Règles absolues
1. JAMAIS inventer d'information
2. Respecter le ton et style existant de Johan
3. Privilégier la concision
4. Confiance > 0.85 pour actions auto-applicables

## Actions disponibles
- score : Évaluer qualité 0-100
- structure : Réorganiser sections
- enrich : Compléter infos manquantes
- summarize : Générer résumé en-tête
- inject_questions : Poser questions stratégiques
- suggest_links : Proposer wikilinks
- cleanup : Supprimer contenu obsolète
- restructure_graph : Proposer split/merge (confiance 0.95 requise)

## Format de réponse
JSON valide avec structure définie.
```

### User Prompt — Base

```jinja2
## Note à analyser

**Titre** : {{ note.title }}
**Type** : {{ metadata.note_type }}
**Mots** : {{ word_count }}
**Dernière modification** : {{ updated_at }}
**Score actuel** : {{ quality_score | default('Non évalué') }}

## Frontmatter
{{ frontmatter_yaml }}

## Contenu
{{ content[:3000] }}

{% if linked_notes %}
## Notes liées (contexte)
{% for title, excerpt in linked_notes.items() %}
### [[{{ title }}]]
{{ excerpt[:200] }}
{% endfor %}
{% endif %}

## Instructions spécifiques
{% include type_template %}

## Réponse attendue
{
  "quality_score": 0-100,
  "reasoning": "Analyse globale",
  "actions": [
    {
      "type": "action_type",
      "target": "section ou champ ciblé",
      "content": "nouveau contenu (si applicable)",
      "confidence": 0.0-1.0,
      "reasoning": "justification"
    }
  ]
}
```

### Instructions par Type

#### PERSONNE
```
Focus pour cette fiche contact :
1. Vérifier que rôle, entreprise et contact sont renseignés
2. La section "Historique" liste-t-elle les interactions récentes ?
3. Y a-t-il des [[Projets]] communs à lier ?
4. Si last_contact > 6 mois, suggérer question "Reprendre contact ?"

Ne jamais supprimer de coordonnées sans haute confiance.
```

#### PROJET
```
Focus pour ce projet :
1. Le statut (actif/pause/terminé) est-il à jour ?
2. Les parties prenantes sont-elles toutes liées [[Nom]] ?
3. La timeline a-t-elle une target_date réaliste ?
4. Y a-t-il des décisions non documentées à extraire ?

Si le projet dépasse 2000 mots, envisager un split.
```

#### RÉUNION
```
Focus pour ce compte-rendu :
1. Tous les participants sont-ils liés [[Nom]] ?
2. Les décisions sont-elles clairement listées ?
3. Les actions ont-elles un responsable assigné ?
4. Le projet associé est-il lié ?

Archivable si > 6 mois et aucune action pending.
```

#### ENTITÉ
```
Focus pour cette organisation :
1. Le secteur/industrie est-il renseigné ?
2. Les contacts clés sont-ils liés [[Nom]] ?
3. Y a-t-il des projets associés à lier ?

Enrichir avec site web si mentionné dans le contenu.
```

#### PROCESSUS
```
Focus pour cette procédure :
1. Les étapes sont-elles numérotées ?
2. Y a-t-il des prérequis à expliciter ?
3. Les cas limites sont-ils documentés ?

Ne pas modifier les étapes validées sans haute confiance.
```

---

## 10. Interface Utilisateur

### Wireframe : Modal Preview Retouche

```
┌─────────────────────────────────────────────────────────┐
│  🔧 Preview Retouche : [[Nom de la note]]          [×]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Qualité : 45% ──────────────────────▶ 72%       │   │
│  │           ████████░░░░░░░░░░  ████████████████░░│   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ── Actions proposées (3) ─────────────────────────    │
│                                                         │
│  ☑ [structure] Réorganiser les sections      92% ✓     │
│     → Ajouter section "Historique"                     │
│                                                         │
│  ☑ [enrich] Compléter informations           87% ✓     │
│     → Rôle : "Directeur technique" (extrait du contenu)│
│                                                         │
│  ☐ [inject_questions] Ajouter question       78%       │
│     → "Quand avez-vous échangé pour la dernière fois ?"│
│                                                         │
│  ── Diff ──────────────────────────────────────────    │
│  ┌─────────────────────────────────────────────────┐   │
│  │ - ## Notes                                      │   │
│  │ + ## Informations                               │   │
│  │ + **Rôle** : Directeur technique                │   │
│  │ +                                               │   │
│  │ + ## Historique                                 │   │
│  │ + - 2026-01: Premier contact                   │   │
│  │ +                                               │   │
│  │ + ## Notes                                      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  [Reporter +24h]   [Ignorer]   [Appliquer sélection ▸] │
└─────────────────────────────────────────────────────────┘
```

### Wireframe : Badge Retouche sur Note

```
┌─────────────────────────────────────────────────┐
│ [[Marc Dupont]]                                 │
│                                                 │
│ ┌───────────────────────────────────────────┐  │
│ │ 🔧 3 améliorations proposées         [Voir] │  │
│ └───────────────────────────────────────────┘  │
│                                                 │
│ ## Informations                                │
│ ...                                            │
└─────────────────────────────────────────────────┘
```

### Wireframe : Page Retouches en Attente

```
┌─────────────────────────────────────────────────────────┐
│ 🔧 Retouches en attente                    [Tout valider]│
├─────────────────────────────────────────────────────────┤
│                                                         │
│ ── Haute confiance (auto-applicable) ──────────────    │
│                                                         │
│ ☑ [[Marc Dupont]]        3 actions    92% moy.  [Voir] │
│ ☑ [[Projet Alpha]]       2 actions    89% moy.  [Voir] │
│                                                         │
│ ── Validation requise ─────────────────────────────    │
│                                                         │
│ ☐ [[Réunion 2026-01-20]] 1 action     74%       [Voir] │
│ ☐ [[Acme Corp]]          2 actions    68% moy.  [Voir] │
│                                                         │
│ ── Stats du jour ──────────────────────────────────    │
│ Retouchées : 12/100  |  Auto-appliquées : 8  |  Pending : 4│
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Composants à Créer

| Composant | Basé sur | Rôle |
|-----------|----------|------|
| `RetoucheDiff.svelte` | `Modal` + `VersionDiff` | Modal preview avec actions sélectionnables |
| `RetoucheBadge.svelte` | `Badge` | Indicateur sur note avec actions pending |
| `RetoucheQueue.svelte` | `RetoucheHistory` | Page des retouches en attente |
| `ActionCheckbox.svelte` | — | Action avec checkbox, confiance, preview |

---

## 11. Actions Proactives

### Nouvelles actions suggérées par la Retouche

| Action | Type de note | Description |
|--------|--------------|-------------|
| `suggest_contact` | PERSONNE | "Reprendre contact avec X (dernier échange > 3 mois)" |
| `suggest_task` | PROJET | "Prochaine étape : valider le budget avec [[Marc]]" |
| `profile_insight` | PERSONNE | Ajouter profil psychologique pour mieux communiquer |
| `create_omnifocus` | PROJET, RÉUNION | Créer tâche OmniFocus pour action identifiée |
| `flag_stale` | PROJET | Alerter si projet sans activité > 30 jours |

### Profil Psychologique (PERSONNE)

L'IA analyse le contenu et l'historique pour suggérer :

```markdown
## Profil Communication

**Style** : Formel / Direct / Technique
**Préférences** : Email > Appel > Message
**Disponibilité** : Mardi après-midi
**Points d'attention** : Sensible aux délais, apprécie les résumés

> Suggestion générée par Scapin — à valider
```

### Intégration OmniFocus

Quand une action est identifiée :

1. Retouche détecte une action implicite dans la note
2. Propose `create_omnifocus` avec confiance
3. Si validée → Figaro crée la tâche via `OmniFocusClient`

```python
RetoucheAction(
    type="create_omnifocus",
    content="Valider budget Projet Alpha avec Marc",
    target="Projet Alpha",
    confidence=0.87,
    metadata={"due_date": "2026-02-01", "project": "Travail"}
)
```

---

## 12. Intégration Filage/Lecture

### Cycle complet

```
FILAGE (matin)
    │
    ├── Sélectionne notes prioritaires
    │
    └── Pour chaque note :
            │
            ├── LECTURE (humain) → Johan revoit et rate 0-5
            │       │
            │       └── SM-2 Lecture mis à jour
            │
            └── RETOUCHE (IA) → Améliorations automatiques
                    │
                    └── SM-2 Retouche mis à jour
```

### Deux cycles SM-2 indépendants

| Cycle | Métadonnées | Déclencheur |
|-------|-------------|-------------|
| **Lecture** | `lecture_next`, `lecture_ef` | Filage matinal |
| **Retouche** | `retouche_next`, `retouche_ef` | Background worker |

### Coordination

- Une note peut être due pour Lecture ET Retouche le même jour
- **Ordre** : Retouche AVANT Lecture (note améliorée avant révision humaine)
- **Filage** : Inclut les notes récemment retouchées (catégorie "✨ Améliorées")

---

## 13. Gestion des Erreurs IA

### Types d'erreurs

| Erreur | Cause | Action |
|--------|-------|--------|
| `RateLimitError` | Trop de requêtes | Retry avec backoff exponentiel |
| `InvalidJSONError` | Réponse malformée | Fallback rule-based |
| `TimeoutError` | Requête > 30s | Skip + log + retry plus tard |
| `RefusalError` | Claude refuse | Log + marquer note pour review manuel |
| `LowConfidenceError` | Toutes actions < 50% | Escalade Opus ou skip |

### Fallback Rule-Based

Si l'IA échoue, appliquer des règles simples :

```python
def _rule_based_analysis(note: Note) -> list[RetoucheAction]:
    actions = []

    # Score basé sur structure
    actions.append(RetoucheAction(type="score", ...))

    # Si pas de résumé et > 500 mots
    if not has_summary and word_count > 500:
        actions.append(RetoucheAction(type="summarize", confidence=0.6))

    # Si dernière modif > 6 mois
    if last_modified > 6_months_ago:
        actions.append(RetoucheAction(type="inject_questions",
            content="Cette note est-elle toujours à jour ?"))

    return actions
```

### Logging et Alertes

```python
logger.error("Retouche failed", extra={
    "note_id": note_id,
    "error_type": "InvalidJSONError",
    "model": "haiku",
    "prompt_tokens": 1500,
    "will_retry": True
})
```

---

## 14. Historique et Rollback

### Stockage de l'historique

Chaque retouche est enregistrée dans `enrichment_history` :

```python
EnrichmentRecord(
    timestamp=datetime.now(),
    action_type="structure",
    target="## Historique",
    content="- 2026-01: Premier contact",
    content_before="(contenu original)",  # NOUVEAU
    confidence=0.92,
    applied=True,
    reasoning="[haiku] Section manquante détectée"
)
```

### Git comme backup

Les notes sont dans un repo Git. Chaque retouche = commit automatique.

```bash
# Voir l'historique
git log --oneline -- "Personnes/Marc Dupont.md"

# Revenir à une version
git checkout abc123 -- "Personnes/Marc Dupont.md"
```

### Rollback UI

**Endpoint** : `POST /notes/{id}/rollback`

```typescript
interface RollbackRequest {
  record_index: number;  // Index dans enrichment_history
  // OU
  git_commit: string;    // Hash du commit à restaurer
}
```

**UI** : Dans RetoucheHistory, bouton "Annuler" sur chaque action récente.

---

## 15. Métriques de Succès

| Métrique | Cible |
|----------|-------|
| Notes retouchées/jour | 10-20 |
| Taux d'application auto | > 70% |
| Taux de rejet utilisateur | < 10% |
| Coût IA mensuel | < $5 |
| Temps moyen retouche | < 10s |
| Rollbacks/semaine | < 2 |
| Tâches OmniFocus créées/semaine | 5-10 |

---

## 16. Système de Notifications

### Objectif

Alerter Johan des retouches importantes sans l'inonder de notifications mineures.

### Types de Notifications Retouche

| Type | Priorité | Déclencheur | Canal |
|------|----------|-------------|-------|
| `retouche_important` | HIGH | Action proactive détectée | Toast + Panel + Filage |
| `retouche_pending` | MEDIUM | Actions en attente validation | Panel + Filage |
| `retouche_auto` | LOW | Retouches auto-appliquées | Panel uniquement |
| `retouche_error` | HIGH | Échec répété sur une note | Toast + Panel |

### Déclencheurs d'Alertes Importantes

```python
# Conditions pour notification prioritaire
IMPORTANT_TRIGGERS = [
    # Contact à réactiver
    {
        "type": "suggest_contact",
        "condition": "last_contact > 90 jours",
        "message": "💬 Reprendre contact avec [[{name}]] ?"
    },
    # Projet stagnant
    {
        "type": "flag_stale",
        "condition": "projet.last_activity > 30 jours AND status == 'actif'",
        "message": "⏸️ [[{project}]] semble en pause depuis 30j"
    },
    # Tâche OmniFocus suggérée
    {
        "type": "create_omnifocus",
        "condition": "confidence >= 0.87",
        "message": "✅ Créer tâche : {task_description} ?"
    },
    # Doublon détecté
    {
        "type": "duplicate_detected",
        "condition": "similarity > 0.80",
        "message": "🔀 [[{note1}]] et [[{note2}]] semblent similaires"
    },
    # Split suggéré
    {
        "type": "restructure_graph",
        "condition": "confidence >= 0.90",
        "message": "📂 [[{note}]] pourrait être divisée en sous-notes"
    }
]
```

### Intégration Notification Center

Le `NotificationCenter` existant sera réutilisé :

```typescript
// Nouveau type dans NotificationType
export type NotificationType =
  | ... existing types ...
  | 'NOTE_ENRICHED'      // Déjà existant
  | 'RETOUCHE_IMPORTANT' // Nouveau
  | 'RETOUCHE_PENDING'   // Nouveau
  | 'RETOUCHE_ERROR';    // Nouveau

// Structure notification Retouche
interface RetoucheNotification {
  type: 'RETOUCHE_IMPORTANT' | 'RETOUCHE_PENDING' | 'RETOUCHE_ERROR';
  note_id: string;
  note_title: string;
  action_type: string;
  message: string;
  confidence?: number;
  actions?: NotificationAction[];
}
```

### Actions dans les Notifications

```typescript
// Actions possibles sur une notification Retouche
interface NotificationAction {
  label: string;
  action: 'apply' | 'dismiss' | 'view' | 'snooze';
  metadata?: Record<string, any>;
}

// Exemple : notification tâche OmniFocus
{
  type: 'RETOUCHE_IMPORTANT',
  message: "✅ Créer tâche : Valider budget avec Marc ?",
  actions: [
    { label: "Créer", action: "apply" },
    { label: "Voir note", action: "view" },
    { label: "+24h", action: "snooze", metadata: { hours: 24 } },
    { label: "Ignorer", action: "dismiss" }
  ]
}
```

### Intégration Filage

Le Filage matinal inclut une nouvelle catégorie :

```python
# Dans briefing/filage.py
FILAGE_CATEGORIES = [
    "📥 Nouveaux",           # Emails/events à traiter
    "📚 Lectures du jour",   # Notes SM-2 dues
    "✨ Améliorées",         # Notes retouchées récemment
    "🔧 Alertes Retouche",   # NOUVEAU : Actions importantes
    "⏰ Rappels",            # Tâches dues
    "📊 Stats"               # Métriques du jour
]

# Contenu de "🔧 Alertes Retouche"
def _build_retouche_alerts() -> list[FilageItem]:
    """Sélectionne les alertes Retouche pour le Filage."""
    alerts = []

    # 1. Contacts à réactiver (max 3)
    stale_contacts = get_stale_contacts(days=90, limit=3)
    for contact in stale_contacts:
        alerts.append(FilageItem(
            category="🔧 Alertes Retouche",
            title=f"💬 [[{contact.name}]]",
            subtitle="Dernier échange > 3 mois",
            action_url=f"/memoires/{contact.path}"
        ))

    # 2. Projets stagnants (max 2)
    stale_projects = get_stale_projects(days=30, limit=2)
    for project in stale_projects:
        alerts.append(FilageItem(
            category="🔧 Alertes Retouche",
            title=f"⏸️ [[{project.name}]]",
            subtitle="Sans activité depuis 30j",
            action_url=f"/memoires/{project.path}"
        ))

    # 3. Tâches suggérées (max 3)
    suggested_tasks = get_pending_omnifocus_suggestions(limit=3)
    for task in suggested_tasks:
        alerts.append(FilageItem(
            category="🔧 Alertes Retouche",
            title=f"✅ {task.description[:40]}",
            subtitle=f"Confiance: {task.confidence:.0%}",
            action_url=f"/memoires/{task.note_path}?action=create_task"
        ))

    return alerts
```

### Wireframe : Notification Panel

```
┌─────────────────────────────────────────────────┐
│ 🔔 Notifications                           [×]  │
├─────────────────────────────────────────────────┤
│                                                 │
│ ── Aujourd'hui ──────────────────────────────  │
│                                                 │
│ 🔧 Retouche importante               il y a 2h │
│    💬 Reprendre contact avec [[Marc Dupont]] ? │
│    [Voir note]  [+24h]  [Ignorer]              │
│                                                 │
│ 🔧 Retouche importante               il y a 4h │
│    ✅ Créer tâche : Valider budget Alpha ?     │
│    [Créer]  [Voir]  [Ignorer]                  │
│                                                 │
│ ── Hier ─────────────────────────────────────  │
│                                                 │
│ ✨ 3 notes améliorées automatiquement          │
│    [[Note A]], [[Note B]], [[Note C]]          │
│                                                 │
│ ⚠️ Retouche échouée                            │
│    [[Note problématique]] - JSON invalide      │
│    [Réessayer]  [Ignorer]                      │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Règles de Non-Spam

```python
# Limites pour éviter le spam
NOTIFICATION_LIMITS = {
    "retouche_auto": 0,           # Jamais de toast (panel only)
    "retouche_pending": 3,        # Max 3 toasts/jour
    "retouche_important": 5,      # Max 5 toasts/jour
    "retouche_error": 2,          # Max 2 toasts/jour

    "filage_alerts": 8,           # Max 8 alertes dans Filage
    "panel_retention": 7,         # Jours de rétention panel
}

# Agrégation intelligente
# Si 5+ notes auto-retouchées en 1h → une seule notification groupée
def _aggregate_auto_notifications(notifications: list) -> list:
    if len(notifications) > 5:
        return [GroupedNotification(
            message=f"✨ {len(notifications)} notes améliorées",
            details=[n.note_title for n in notifications]
        )]
    return notifications
```

---

## 17. Migration Lazy des Notes Existantes

### Stratégie

**Principe** : Ne pas migrer en batch. Retoucher les notes au fil de l'eau.

### Mécanisme

```python
async def get_notes_for_retouche(limit: int = 10) -> list[Note]:
    """Sélectionne les notes à retoucher selon priorité."""

    # 1. Notes dues selon SM-2 (déjà retouchées au moins une fois)
    due_notes = await db.fetch("""
        SELECT * FROM notes
        WHERE retouche_next < NOW()
        ORDER BY retouche_next ASC
        LIMIT ?
    """, limit // 2)

    # 2. Notes jamais retouchées (migration lazy)
    # Priorise : récemment modifiées, qualité inconnue
    never_retouched = await db.fetch("""
        SELECT * FROM notes
        WHERE retouche_count = 0 OR retouche_count IS NULL
        ORDER BY
            CASE WHEN quality_score IS NULL THEN 0 ELSE 1 END,
            updated_at DESC
        LIMIT ?
    """, limit - len(due_notes))

    return due_notes + never_retouched
```

### Initialisation des Métadonnées

Quand une note est retouchée pour la première fois :

```python
async def _initialize_retouche_metadata(note: Note) -> None:
    """Initialise les champs SM-2 pour une note jamais retouchée."""

    if note.retouche_count is None:
        note.retouche_count = 0
        note.retouche_ef = 2.5  # EF par défaut
        note.retouche_interval = 0
        note.retouche_next = datetime.now()  # Due maintenant

        await note_manager.save_metadata(note)
```

### Estimation de Couverture

```
Avec 10-20 notes/jour :
- 1 semaine  → ~100 notes (notes critiques couvertes)
- 1 mois     → ~500 notes (majorité du corpus actif)
- 3 mois     → ~1500 notes (couverture quasi-complète)
```

### Priorisation Lazy

| Priorité | Critère | Ratio |
|----------|---------|-------|
| 1 | Notes liées à un email récent | 30% |
| 2 | Notes PROJET ou PERSONNE actives | 30% |
| 3 | Notes récemment modifiées | 20% |
| 4 | Notes jamais évaluées | 20% |

### Indicateur de Progression

Dans le dashboard Valets :

```
┌─────────────────────────────────────────────────┐
│ 🔧 Retouche - Couverture                        │
├─────────────────────────────────────────────────┤
│                                                 │
│ Notes retouchées : 347 / 1,234 (28%)            │
│ ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░        │
│                                                 │
│ Par type :                                      │
│   PERSONNE  ████████████████████░░ 85%          │
│   PROJET    ████████████████░░░░░░ 67%          │
│   RÉUNION   ████████░░░░░░░░░░░░░░ 34%          │
│   ENTITÉ    ██████░░░░░░░░░░░░░░░░ 23%          │
│   AUTRE     ██░░░░░░░░░░░░░░░░░░░░ 8%           │
│                                                 │
│ Estimation couverture complète : ~45 jours      │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Pas de Migration Forcée

**Avantages du lazy** :
- Pas de pic de coût IA
- Notes actives traitées en premier
- Notes obsolètes naturellement ignorées
- Feedback utilisateur intégré progressivement

**À éviter** :
- Script de migration batch
- Traitement de nuit intensif
- Forcer la retouche de tout le corpus

---

## 18. Conformité CLAUDE.md & Skills

### Fichiers Critiques — Confirmation Requise

**⚠️ Phase 0 modifie un fichier critique :**

| Fichier | Phase | Modification | Risque |
|---------|-------|--------------|--------|
| `src/sancho/multi_pass_analyzer.py` | 0 | Hériter de AnalysisEngine | **CRITIQUE** - Confirmation Johan |

→ **Ne pas commencer Phase 0 sans accord explicite de Johan.**

### Conventions Backend (skill `/api`)

**Pattern obligatoire pour endpoints Retouche :**

```python
# src/frontin/api/routers/retouche.py
from src.frontin.api.models.responses import APIResponse
from src.monitoring.logger import get_logger

logger = get_logger("frontin.api.retouche")

@router.post("/notes/{note_id}/retouche/preview", response_model=APIResponse[RetouchePreviewResponse])
async def preview_retouche(
    request: Request,
    note_id: str,
    service: RetoucheService = Depends(get_retouche_service),  # async def
) -> APIResponse[RetouchePreviewResponse]:
    """Preview retouche actions for a note."""
    correlation_id = request.headers.get("X-Correlation-ID", "unknown")

    try:
        preview = await service.preview(note_id)  # Logique dans service
        return APIResponse(success=True, data=preview)
    except ScapinError as e:
        logger.error(f"Retouche preview failed: {e}", extra={"correlation_id": correlation_id, "note_id": note_id})
        raise HTTPException(status_code=400, detail=e.message)
```

**Checklist API :**
- [ ] `async def` pour endpoints ET dependencies
- [ ] Logique métier dans `RetoucheService`, pas dans endpoint
- [ ] `correlation_id` dans tous les logs
- [ ] Pydantic models pour request/response
- [ ] Docstring pour OpenAPI

### Conventions Frontend (skill `/ui`)

**Composants Retouche — Patterns obligatoires :**

```svelte
<!-- RetoucheDiff.svelte -->
<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    noteId: string;
    actions: RetoucheAction[];
    onApply?: (selected: string[]) => void;
    onDismiss?: () => void;
  }

  let { noteId, actions, onApply, onDismiss }: Props = $props();

  // $derived pour calculs
  const selectedActions = $derived(actions.filter(a => a.selected));
  const avgConfidence = $derived(
    selectedActions.length > 0
      ? selectedActions.reduce((sum, a) => sum + a.confidence, 0) / selectedActions.length
      : 0
  );

  // $effect UNIQUEMENT pour side effects
  $effect(() => {
    // Log pour analytics (side effect)
    logger.info('Preview opened', { noteId, actionCount: actions.length });
  });
</script>

<!-- Accessibilité obligatoire -->
<div
  role="dialog"
  aria-modal="true"
  aria-labelledby="retouche-title"
  class="glass glass-solid"
>
  <h2 id="retouche-title">Preview Retouche</h2>
  <!-- ... -->
</div>
```

**Checklist UI :**
- [ ] `$derived` pour calculs, `$effect` pour side effects uniquement
- [ ] Interface Props typée
- [ ] Accessibilité : `role`, `aria-*`, keyboard navigation
- [ ] Liquid Glass : classes `glass`, `glass-interactive`
- [ ] Dark mode : CSS variables
- [ ] Loading/Error states
- [ ] `data-testid` pour E2E

### Commits Atomiques par Phase

| Phase | Commits suggérés |
|-------|------------------|
| 0 | `refactor(sancho): extract AnalysisEngine base class` |
| 1 | `feat(passepartout): implement retouche AI connection` |
| 2 | `feat(templates): add retouche prompts per note type` |
| 3 | `feat(passepartout): add suggest_links action` <br> `feat(passepartout): add cleanup action` <br> `feat(figaro): add create_omnifocus action` |
| 4 | `feat(ui): add RetoucheDiff modal component` <br> `feat(ui): add RetoucheBadge component` <br> `feat(api): add retouche preview endpoint` |
| 5 | `feat(ui): add RetoucheQueue page` <br> `feat(api): add retouche rollback endpoint` |
| 6 | `feat(notifications): add retouche notification types` <br> `feat(briefing): add retouche alerts to filage` |
| 7 | `test(retouche): add unit tests` <br> `test(e2e): add retouche E2E tests` |

### Documentation à Mettre à Jour

| Phase | Documentation |
|-------|---------------|
| Fin Phase 1 | `ARCHITECTURE.md` — Section Retouche |
| Fin Phase 4 | `docs/user-guide/notes.md` — Bouton Retouche |
| Fin Phase 5 | `docs/user-guide/notes.md` — Page Retouches |
| Fin Phase 6 | `docs/user-guide/notifications.md` — Alertes Retouche |

### Checklist Bloquante par Phase

**À valider avant chaque commit :**

```
□ Documentation mise à jour (ARCHITECTURE.md / user-guide)
□ Tests E2E pour UI (Playwright)
□ Tests unitaires pour backend (pytest)
□ Test manuel effectué — décrire ce qui a été vérifié
□ Logs vérifiés — aucun ERROR/WARNING nouveau
□ Ruff : 0 warning
□ TypeScript : npm run check passe
□ Pas de TODO, code commenté, console.log
```

### Tests — Cas d'Erreur Obligatoires

**Phase 7 doit inclure :**

```python
# tests/unit/test_retouche_reviewer.py

class TestRetoucheReviewer:
    # Happy path
    def test_review_note_returns_actions(self, reviewer, sample_note):
        ...

    # CAS D'ERREUR OBLIGATOIRES
    def test_handles_empty_note(self, reviewer):
        """Test avec note vide."""
        result = reviewer.review(Note(content=""))
        assert result.actions == []
        assert result.quality_score == 0

    def test_handles_ai_timeout(self, reviewer, mock_ai_client):
        """Test de timeout IA."""
        mock_ai_client.call.side_effect = TimeoutError()
        result = reviewer.review(sample_note)
        # Doit fallback sur rule-based
        assert result.fallback_used is True

    def test_handles_invalid_json_response(self, reviewer, mock_ai_client):
        """Test réponse JSON malformée."""
        mock_ai_client.call.return_value = "not json"
        result = reviewer.review(sample_note)
        assert result.error == "InvalidJSONError"

    def test_escalates_on_low_confidence(self, reviewer, mock_ai_client):
        """Test escalade modèle si confiance < 70%."""
        mock_ai_client.call.return_value = {"confidence": 50}
        result = reviewer.review(sample_note)
        assert mock_ai_client.call.call_count >= 2  # Escalade
```

```typescript
// web/e2e/retouche.spec.ts

test.describe('Retouche', () => {
  // Happy path
  test('displays preview modal', async ({ page }) => { ... });

  // CAS D'ERREUR OBLIGATOIRES
  test('handles API error gracefully', async ({ page }) => {
    await page.route('**/api/notes/*/retouche/preview', route =>
      route.fulfill({ status: 500, body: JSON.stringify({ error: 'Server error' }) })
    );
    await page.click('[data-testid="retouche-button"]');
    await expect(page.locator('[data-testid="error-toast"]')).toBeVisible();
  });

  test('handles empty actions list', async ({ page }) => {
    await page.route('**/api/notes/*/retouche/preview', route =>
      route.fulfill({ status: 200, body: JSON.stringify({ success: true, data: { actions: [] } }) })
    );
    await page.click('[data-testid="retouche-button"]');
    await expect(page.locator('[data-testid="no-actions-message"]')).toBeVisible();
  });

  test('keyboard navigation works', async ({ page }) => {
    await page.click('[data-testid="retouche-button"]');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Space'); // Toggle action
    await page.keyboard.press('Escape'); // Close modal
    await expect(page.locator('[role="dialog"]')).not.toBeVisible();
  });
});
```

---

## 19. Résumé des Phases

| Phase | Contenu | Fichiers Principaux | Commits |
|-------|---------|---------------------|---------|
| **0** | Refactoring AnalysisEngine | `src/sancho/analysis_engine.py` | 1 |
| **1** | Connexion IA | `retouche_reviewer.py` | 1 |
| **2** | Prompts par type | `templates/ai/v2/retouche/*.j2` | 1 |
| **3** | Actions avancées | `retouche_reviewer.py` | 3 |
| **4** | Preview UI | `RetoucheDiff.svelte`, `RetoucheBadge.svelte` | 3 |
| **5** | Queue + Rollback | `RetoucheQueue.svelte` | 2 |
| **6** | Notifications | `notification_service.py`, `briefing/filage.py` | 2 |
| **7** | Tests | `test_retouche_reviewer.py`, `retouche.spec.ts` | 2 |

**Total estimé : 15 commits atomiques**

---

## 20. Prérequis Avant Implémentation

Avant de commencer Phase 0 :

```
□ Confirmation Johan pour modifier multi_pass_analyzer.py (fichier critique)
□ Branche hygiene-des-notes créée ✓
□ Plan relu et approuvé
```
