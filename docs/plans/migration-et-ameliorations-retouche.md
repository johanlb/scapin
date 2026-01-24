# Plan : Migration et Améliorations Retouche

**Version** : v3.1 (contexte IA enrichi + modèles PKM)

## Objectif

Fusionner `NoteReviewer` dans `RetoucheReviewer` pour éliminer le doublon de processus tout en **enrichissant significativement le contexte fourni à l'IA**.

---

## Problème critique identifié

### Contexte actuel (insuffisant)

`RetoucheReviewer._load_context()` fournit uniquement :
- Notes liées par wikilinks explicites (max 10)
- Métriques basiques (word_count, has_summary, section_count)

### Contexte disponible mais non utilisé

Le système dispose de capacités bien plus riches via `ContextSearcher` (utilisé pour Multi-Pass emails) :

| Source | Outil | Usage potentiel |
|--------|-------|-----------------|
| **Notes sémantiquement similaires** | FAISS via `search_notes()` | Trouver des notes connexes non liées |
| **Recherche par entités** | `EntitySearcher` | Trouver les notes sur les personnes/projets mentionnés |
| **Événements calendrier** | `CrossSourceEngine` | RDV liés à la personne/projet |
| **Historique email** | `CrossSourceEngine` | Échanges récents |
| **Tâches OmniFocus** | `CrossSourceEngine` | Tâches existantes liées |
| **Historique Git** | `git_manager` | Modifications récentes de la note |

### Impact

Sans ce contexte, l'IA Retouche :
- Ne peut pas suggérer de liens vers des notes pertinentes non liées
- Ne peut pas détecter les doublons ou notes à fusionner
- Ne peut pas enrichir avec des informations d'autres sources
- Propose des actions moins pertinentes

---

## Analyse d'impact

### Fichiers critiques (confirmation requise)
- `src/passepartout/note_manager.py` — Utilisé par les deux reviewers (pas modifié directement)
- `src/passepartout/retouche_reviewer.py` — Cible de la fusion (~200 lignes ajoutées)

### Fonctionnalités à migrer

| Fonctionnalité | Source | Justification |
|----------------|--------|---------------|
| **HygieneMetrics** | note_reviewer.py:94-108 | Métriques essentielles pour qualité |
| **_scrub_content()** | note_reviewer.py:536-548 | Économie tokens IA (critique coût) |
| **_calculate_hygiene_metrics()** | note_reviewer.py:433-529 | Détection problèmes structurels |
| **_check_temporal_references()** | note_reviewer.py:660-698 | Détection contenu obsolète |
| **_check_completed_tasks()** | note_reviewer.py:701-737 | Nettoyage tâches terminées |
| **_check_missing_links()** | note_reviewer.py:739-772 | Amélioration connectivité |
| **_check_formatting()** | note_reviewer.py:774-801 | Corrections mécaniques |
| **CrossSourceEngine** | note_reviewer.py:362-431 | **UTILISÉ** par context_searcher.py |

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
MERGE → MERGE_INTO
SPLIT, REFACTOR → RESTRUCTURE_GRAPH
```

---

## Plan d'exécution (commits atomiques)

### Commit 1 : Ajouter types et dataclasses à RetoucheReviewer

**Fichiers modifiés :**
- `src/passepartout/retouche_reviewer.py`

**Changements :**
```python
# Ajouter à RetoucheAction
FORMAT = "format"
VALIDATE = "validate"
FIX_LINKS = "fix_links"

# Ajouter dataclass HygieneMetrics
@dataclass
class HygieneMetrics:
    word_count: int
    is_too_short: bool
    is_too_long: bool
    frontmatter_valid: bool
    frontmatter_issues: list[str] = field(default_factory=list)
    broken_links: list[str] = field(default_factory=list)
    heading_issues: list[str] = field(default_factory=list)
    duplicate_candidates: list[tuple[str, float]] = field(default_factory=list)
    formatting_score: float = 1.0

# Ajouter à RetoucheContext
hygiene: Optional[HygieneMetrics] = None
```

**Vérification :**
```bash
.venv/bin/ruff check src/passepartout/retouche_reviewer.py
.venv/bin/pytest tests/unit/test_retouche_reviewer.py -v
```

---

### Commit 2 : Migrer méthodes utilitaires

**Fichiers modifiés :**
- `src/passepartout/retouche_reviewer.py`

**Méthodes à copier :**
- `_scrub_content()` — Nettoie images/médias avant analyse IA
- `_calculate_hygiene_metrics()` — Calcule métriques structurelles
- `_extract_wikilinks()` — Extrait `[[liens]]` (si pas déjà présent)

**Vérification :**
```bash
.venv/bin/pytest tests/unit/test_retouche_reviewer.py -v
# Vérifier logs pour erreurs
```

---

### Commit 3 : Migrer analyses rule-based

**Fichiers modifiés :**
- `src/passepartout/retouche_reviewer.py`

**Méthodes à copier :**
- `_check_temporal_references()` — Détection références datées
- `_check_completed_tasks()` — Détection `[x]` archivables
- `_check_missing_links()` — Suggestions wikilinks
- `_check_formatting()` — Problèmes de formatage

**Intégration dans `review_note()` :**
```python
# Avant analyse IA
hygiene = self._calculate_hygiene_metrics(note)
scrubbed = self._scrub_content(note.content)

# Analyses rule-based (génèrent des actions)
rule_actions = []
rule_actions.extend(self._check_temporal_references(scrubbed))
rule_actions.extend(self._check_completed_tasks(scrubbed))
rule_actions.extend(self._check_missing_links(scrubbed, context.linked_notes))
rule_actions.extend(self._check_formatting(scrubbed))

# Puis analyse IA sur contenu scrubbed
```

**Vérification :**
```bash
.venv/bin/pytest tests/unit/test_retouche_reviewer.py -v
.venv/bin/python -m src.frontin.cli notes review --process --limit 1 --force
```

---

### Commit 4 : Enrichir le contexte IA (CRITIQUE)

**Objectif** : Fournir à l'IA Retouche un contexte aussi riche que celui du Multi-Pass emails.

**Fichiers modifiés :**
- `src/passepartout/retouche_reviewer.py`

#### 4.1 Étendre RetoucheContext

```python
@dataclass
class RetoucheContext:
    """Context collected for Retouche analysis"""

    note: Note
    metadata: NoteMetadata

    # Contexte existant (wikilinks)
    linked_notes: list[Note] = field(default_factory=list)
    linked_note_excerpts: dict[str, str] = field(default_factory=dict)

    # NOUVEAU: Notes sémantiquement similaires (FAISS)
    similar_notes: list[tuple[str, str, float]] = field(default_factory=list)
    # Format: [(note_id, title, relevance_score), ...]

    # NOUVEAU: Contexte cross-source
    related_calendar_events: list[dict] = field(default_factory=list)
    related_emails: list[dict] = field(default_factory=list)
    related_tasks: list[dict] = field(default_factory=list)

    # NOUVEAU: Profils d'entités mentionnées
    entity_profiles: dict[str, dict] = field(default_factory=dict)
    # Format: {"Nom Entité": {"type": "personne", "role": "...", ...}}

    # NOUVEAU: Historique Git
    recent_changes: list[dict] = field(default_factory=list)

    # Métriques existantes
    word_count: int = 0
    has_summary: bool = False
    section_count: int = 0
    question_count: int = 0
    hygiene: Optional[HygieneMetrics] = None
```

#### 4.2 Modifier le constructeur

```python
def __init__(
    self,
    note_manager: NoteManager,
    metadata_store: NoteMetadataStore,
    scheduler: NoteScheduler,
    ai_router: Optional["AIRouter"] = None,
    cross_source_engine: Optional["CrossSourceEngine"] = None,  # NOUVEAU
    context_searcher: Optional["ContextSearcher"] = None,       # NOUVEAU
):
    self.notes = note_manager
    self.store = metadata_store
    self.scheduler = scheduler
    self.ai_router = ai_router
    self.cross_source = cross_source_engine

    # NOUVEAU: Utiliser ContextSearcher pour recherche unifiée
    self._context_searcher = context_searcher
    if context_searcher is None and cross_source_engine is not None:
        from src.sancho.context_searcher import ContextSearcher
        self._context_searcher = ContextSearcher(
            note_manager=note_manager,
            cross_source_engine=cross_source_engine,
        )
```

#### 4.3 Réécrire `_load_context()`

```python
async def _load_context(
    self,
    note: Note,
    metadata: NoteMetadata,
) -> RetoucheContext:
    """Load enriched context for Retouche analysis"""

    # 1. Notes liées par wikilinks (existant)
    wikilinks = self._extract_wikilinks(note.content)
    linked_notes, linked_excerpts = self._load_linked_notes(wikilinks)

    # 2. NOUVEAU: Notes sémantiquement similaires (FAISS)
    similar_notes = self._find_similar_notes(note, exclude=wikilinks)

    # 3. NOUVEAU: Contexte cross-source via ContextSearcher
    calendar_events = []
    emails = []
    tasks = []
    entity_profiles = {}

    if self._context_searcher:
        # Extraire les entités mentionnées dans la note
        entities = self._extract_entities_from_content(note)

        # Rechercher le contexte pour ces entités
        context_result = await self._context_searcher.search_for_entities(
            entities=entities,
            config=ContextSearchConfig(
                max_notes=5,
                max_calendar_events=5,
                max_emails=3,
                include_calendar=True,
                include_tasks=True,
                include_emails=True,
            ),
        )

        calendar_events = [e.__dict__ for e in context_result.calendar]
        emails = [e.__dict__ for e in context_result.emails]
        tasks = [t.__dict__ for t in context_result.tasks]
        entity_profiles = {
            name: profile.__dict__
            for name, profile in context_result.entity_profiles.items()
        }

    # 4. NOUVEAU: Historique Git
    recent_changes = self._load_git_history(note)

    # 5. Métriques
    word_count = len(note.content.split())
    has_summary = self._has_summary(note.content)
    section_count = len(re.findall(r"^##\s", note.content, re.MULTILINE))
    question_count = note.content.count("?")

    return RetoucheContext(
        note=note,
        metadata=metadata,
        linked_notes=linked_notes,
        linked_note_excerpts=linked_excerpts,
        similar_notes=similar_notes,
        related_calendar_events=calendar_events,
        related_emails=emails,
        related_tasks=tasks,
        entity_profiles=entity_profiles,
        recent_changes=recent_changes,
        word_count=word_count,
        has_summary=has_summary,
        section_count=section_count,
        question_count=question_count,
    )
```

#### 4.4 Nouvelles méthodes à ajouter

```python
def _find_similar_notes(
    self,
    note: Note,
    exclude: list[str],
    top_k: int = 5,
) -> list[tuple[str, str, float]]:
    """Find semantically similar notes via FAISS"""
    try:
        results = self.notes.search_notes(
            query=f"{note.title} {note.content[:500]}",
            top_k=top_k + len(exclude) + 1,
            return_scores=True,
        )

        similar = []
        exclude_set = set(exclude) | {note.title}

        for result_note, score in results:
            if result_note.title not in exclude_set:
                similar.append((result_note.note_id, result_note.title, score))
                if len(similar) >= top_k:
                    break

        return similar
    except Exception as e:
        logger.warning(f"Similar notes search failed: {e}")
        return []

def _extract_entities_from_content(self, note: Note) -> list[str]:
    """Extract entity names from note for context search"""
    entities = [note.title]

    # Ajouter les tags pertinents
    if note.tags:
        entities.extend(note.tags[:3])

    # Extraire les noms propres (mots capitalisés)
    import re
    pattern = r"\b([A-Z][a-zàâäéèêëïîôùûü]+(?:\s+[A-Z][a-zàâäéèêëïîôùûü]+)*)\b"
    names = re.findall(pattern, note.content)
    entities.extend(names[:5])

    return list(set(entities))

def _load_git_history(self, note: Note, limit: int = 5) -> list[dict]:
    """Load recent Git history for the note"""
    if not hasattr(self.notes, "git_manager") or not self.notes.git_manager:
        return []

    try:
        versions = self.notes.git_manager.get_note_versions(note.note_id, limit=limit)
        return [
            {
                "commit_hash": v.commit_hash,
                "timestamp": v.timestamp.isoformat(),
                "message": v.commit_message,
            }
            for v in versions
        ]
    except Exception as e:
        logger.debug(f"Could not load git history: {e}")
        return []
```

**Vérification :**
```bash
.venv/bin/pytest tests/unit/test_retouche_reviewer.py -v
# Test manuel avec logs verbeux
.venv/bin/python -m src.frontin.cli notes review --process --limit 1 --force
# Vérifier dans les logs que le contexte enrichi est chargé
```

---

### Commit 4b : Mettre à jour le template Retouche (CRITIQUE)

**Objectif** : Afficher le contexte enrichi dans le prompt IA.

**Fichiers modifiés :**
- `templates/ai/v2/retouche/retouche_user.j2`
- `src/sancho/template_renderer.py`

#### Modifier `render_retouche()` dans template_renderer.py

```python
def render_retouche(
    self,
    note: Any,
    note_type: str,
    word_count: int,
    content: str,
    quality_score: Optional[int] = None,
    updated_at: Optional[str] = None,
    frontmatter: Optional[str] = None,
    linked_notes: Optional[dict[str, str]] = None,
    # NOUVEAU: Contexte enrichi
    similar_notes: Optional[list[tuple[str, str, float]]] = None,
    calendar_events: Optional[list[dict]] = None,
    emails: Optional[list[dict]] = None,
    tasks: Optional[list[dict]] = None,
    entity_profiles: Optional[dict[str, dict]] = None,
    recent_changes: Optional[list[dict]] = None,
) -> str:
```

#### Modifier `retouche_user.j2`

```jinja2
{# Retouche User Prompt (DYNAMIC) - v3 avec contexte enrichi #}

## Note à analyser

**Titre** : {{ note.title }}
**Type** : {{ note_type | default('inconnu') }}
**Mots** : {{ word_count }}
**Dernière modification** : {{ updated_at | default('Non disponible') }}
**Score actuel** : {{ quality_score | default('Non évalué') }}

{% if frontmatter %}
## Frontmatter

```yaml
{{ frontmatter }}
```
{% endif %}

## Contenu

{{ content[:3000] }}
{% if content | length > 3000 %}
[... contenu tronqué, {{ content | length }} caractères au total ...]
{% endif %}

{% if linked_notes %}
## Notes liées (wikilinks existants)

{% for title, excerpt in linked_notes.items() %}
### [[{{ title }}]]
{{ excerpt[:200] }}{% if excerpt | length > 200 %}...{% endif %}

{% endfor %}
{% endif %}

{% if similar_notes %}
## Notes similaires (non liées)

Ces notes sont sémantiquement proches mais ne sont pas encore liées par wikilink.
Évalue si des liens seraient pertinents.

{% for note_id, title, score in similar_notes %}
- **[[{{ title }}]]** (similarité: {{ (score * 100) | int }}%)
{% endfor %}
{% endif %}

{% if entity_profiles %}
## Profils des entités mentionnées

{% for name, profile in entity_profiles.items() %}
### {{ name }} ({{ profile.entity_type | default('entité') }})
{% if profile.role %}- **Rôle**: {{ profile.role }}{% endif %}
{% if profile.relationship %}- **Relation**: {{ profile.relationship }}{% endif %}
{% if profile.key_facts %}
- **Faits clés**:
{% for fact in profile.key_facts[:3] %}
  - {{ fact[:100] }}
{% endfor %}
{% endif %}

{% endfor %}
{% endif %}

{% if calendar_events %}
## Événements calendrier liés

{% for event in calendar_events %}
- 📅 {{ event.date }}{% if event.time %} {{ event.time }}{% endif %}: **{{ event.title }}**
{% endfor %}
{% endif %}

{% if tasks %}
## Tâches OmniFocus existantes

{% for task in tasks %}
- ⚡ {{ task.title }}{% if task.project %} [{{ task.project }}]{% endif %}{% if task.due_date %} (due: {{ task.due_date }}){% endif %}
{% endfor %}
{% endif %}

{% if recent_changes %}
## Historique des modifications récentes

{% for change in recent_changes[:3] %}
- {{ change.timestamp[:10] }}: {{ change.message[:50] }}
{% endfor %}
{% endif %}

## Instructions spécifiques

{% include 'retouche/' ~ note_type ~ '.j2' ignore missing %}
{% if not note_type or note_type == 'inconnu' %}
{% include 'retouche/generique.j2' %}
{% endif %}

## Réponse attendue

Réponds en JSON valide avec cette structure exacte :
```json
{
  "quality_score": 0-100,
  "reasoning": "Analyse globale de la note",
  "actions": [
    {
      "type": "action_type",
      "target": "section ou champ ciblé",
      "content": "nouveau contenu (si applicable)",
      "confidence": 0.0-1.0,
      "reasoning": "justification de l'action"
    }
  ]
}
```
```

**Vérification :**
```bash
.venv/bin/ruff check src/sancho/template_renderer.py
# Test que le template se rend correctement
.venv/bin/python -c "from src.sancho.template_renderer import get_template_renderer; r = get_template_renderer(); print(r.list_templates())"
```

---

### Commit 4c : Intégrer les modèles PKM comme référence (CRITIQUE)

**Objectif** : L'IA doit utiliser les modèles de notes de Johan (dans `PKM/Processus/`) comme référence de structure idéale, pas les templates Jinja2 génériques.

**Problème actuel** :
- Johan maintient des modèles détaillés (`Modèle — Fiche Personne.md`, etc.)
- Ces modèles définissent précisément les sections attendues (👤, 🏢, 🧠, 🤝...)
- L'IA Retouche ne les consulte pas → suggestions non alignées

**Fichiers modifiés :**
- `src/passepartout/retouche_reviewer.py`
- `templates/ai/v2/retouche/retouche_user.j2`

#### 4c.1 Ajouter un loader de modèles PKM

```python
# Dans retouche_reviewer.py

# Mapping type de note → titre du modèle PKM
PKM_MODEL_TITLES = {
    "personne": "Modèle — Fiche Personne",
    "projet": "Modèle — Fiche Projet",
    "reunion": "Modèle — Fiche Réunion",
    "entite": "Modèle — Fiche Entité",
    "evenement": "Modèle — Fiche Événement",
}

def _load_pkm_model(self, note_type: str) -> Optional[str]:
    """
    Load the PKM model template for a given note type.

    Searches for notes titled "Modèle — Fiche {Type}" in the PKM.
    Returns the content to use as reference structure.
    """
    model_title = PKM_MODEL_TITLES.get(note_type)
    if not model_title:
        return None

    try:
        results = self.notes.search_notes(query=model_title, top_k=1)
        if results:
            model_note = results[0][0] if isinstance(results[0], tuple) else results[0]
            if model_note.title == model_title:
                # Extraire uniquement la section "STRUCTURE À COPIER"
                content = model_note.content
                start = content.find("━━━ DÉBUT MODÈLE")
                end = content.find("━━━ FIN MODÈLE")
                if start != -1 and end != -1:
                    return content[start:end + len("━━━ FIN MODÈLE ━━━")]
                return content[:2000]  # Fallback: premiers 2000 chars
        return None
    except Exception as e:
        logger.warning(f"Failed to load PKM model for {note_type}: {e}")
        return None
```

#### 4c.2 Étendre RetoucheContext

```python
@dataclass
class RetoucheContext:
    # ... champs existants ...

    # NOUVEAU: Modèle PKM de référence
    pkm_model: Optional[str] = None  # Contenu du modèle pour ce type de note
```

#### 4c.3 Charger le modèle dans `_load_context()`

```python
async def _load_context(self, note: Note, metadata: NoteMetadata) -> RetoucheContext:
    # ... code existant ...

    # NOUVEAU: Charger le modèle PKM correspondant
    note_type = metadata.note_type.value if metadata.note_type else "inconnu"
    pkm_model = self._load_pkm_model(note_type)

    return RetoucheContext(
        # ... champs existants ...
        pkm_model=pkm_model,
    )
```

#### 4c.4 Modifier `_build_retouche_prompt()` pour passer le modèle

```python
def _build_retouche_prompt(self, context: RetoucheContext) -> str:
    # ... code existant ...

    return renderer.render_retouche(
        # ... paramètres existants ...
        pkm_model=context.pkm_model,  # NOUVEAU
    )
```

#### 4c.5 Modifier le template `retouche_user.j2`

Ajouter après la section "Notes liées" :

```jinja2
{% if pkm_model %}
## Modèle de référence PKM

Cette note devrait suivre la structure définie par Johan :

```
{{ pkm_model }}
```

**Instructions** : Compare la note analysée à ce modèle. Suggère des actions pour :
- Ajouter les sections manquantes
- Réorganiser selon la structure du modèle
- Compléter les champs requis
{% endif %}
```

#### 4c.6 Modifier `render_retouche()` dans template_renderer.py

```python
def render_retouche(
    self,
    # ... paramètres existants ...
    pkm_model: Optional[str] = None,  # NOUVEAU
) -> str:
    return self.render(
        "retouche/retouche_user",
        # ... paramètres existants ...
        pkm_model=pkm_model,
    )
```

**Vérification :**
```bash
.venv/bin/pytest tests/unit/test_retouche_reviewer.py -v
# Test manuel : vérifier que le modèle PKM apparaît dans les logs
.venv/bin/python -m src.frontin.cli notes review --process --limit 1 --force
```

**Impact attendu :**
- L'IA connaît maintenant la structure exacte attendue par Johan
- Suggestions de sections manquantes (🧠 PROFIL RELATIONNEL, etc.)
- Meilleur alignement avec les pratiques PKM de Johan

---

### Commit 5 : Adapter background_worker.py

**Fichiers modifiés :**
- `src/passepartout/background_worker.py`

**Changements :**
```python
# Avant
from src.passepartout.note_reviewer import NoteReviewer, ReviewResult
self._reviewer: Optional[NoteReviewer] = None

# Après
# Supprimer import NoteReviewer
# Utiliser uniquement _retouche_reviewer pour les deux cycles
```

**Vérification :**
```bash
.venv/bin/pytest tests/unit/test_background_worker.py -v
# Démarrer worker et vérifier logs
```

---

### Commit 6 : Adapter CLI commande pending

**Fichiers modifiés :**
- `src/frontin/cli.py`

**Changements :**
- Remplacer `ActionType` → `RetoucheAction`
- Remplacer `ReviewAction` → `RetoucheActionResult`
- Adapter appel `_apply_action()`

**Vérification :**
```bash
.venv/bin/python -m src.frontin.cli notes pending list
.venv/bin/python -m src.frontin.cli notes pending approve <note-id> 0
```

---

### Commit 7 : Mettre à jour exports et documentation

**Fichiers modifiés :**
- `src/passepartout/__init__.py` — Exports
- `docs/user-guide/04-notes.md` — Si comportement change
- `ARCHITECTURE.md` — Section Passepartout

**Vérification :**
```bash
.venv/bin/ruff check src/passepartout/__init__.py
```

---

### Commit 8 : Adapter tests

**Fichiers modifiés :**
- `tests/unit/test_retouche_reviewer.py` — Étendre pour nouvelles fonctionnalités
- `tests/unit/test_note_reviewer.py` — Adapter imports ou supprimer

**Stratégie :**
- Conserver les tests de `test_note_reviewer.py` qui testent HygieneMetrics
- Les adapter pour utiliser RetoucheReviewer
- Supprimer les tests redondants

**Vérification :**
```bash
.venv/bin/pytest tests/unit/test_retouche_reviewer.py -v
.venv/bin/pytest tests/ -v  # Tous les tests
```

---

### Commit 9 : Supprimer NoteReviewer

**Fichiers supprimés :**
- `src/passepartout/note_reviewer.py`

**Fichiers modifiés :**
- `src/passepartout/__init__.py` — Retirer exports
- `tests/unit/test_note_reviewer.py` — Supprimer ou renommer

**Vérification finale :**
```bash
.venv/bin/ruff check src/passepartout/
.venv/bin/pytest tests/ -v
.venv/bin/python -m src.frontin.cli notes review --process --limit 3 --force
.venv/bin/python -m src.frontin.cli notes pending list
```

---

## Checklist par commit

```
□ Code modifié
□ Ruff : 0 warning
□ Tests passent
□ Logs vérifiés (pas d'erreur nouvelle)
□ Test manuel effectué
□ Documentation mise à jour (si applicable)
```

---

## Risques et mitigations

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Régression cycle Lecture | Haut | Test E2E complet après commit 5 |
| Perte fonctionnalité CrossSource | Haut | Commit dédié (4) avec tests |
| Breaking changes API | Moyen | Pas de changement API publique |
| Tests flaky | Moyen | Exécuter 2x avant merge |
| **Performance ContextSearcher** | Moyen | Cache TTL 60s déjà en place, limiter max_results |
| **Coût tokens IA augmenté** | Moyen | Le contexte enrichi augmente le prompt (~500-1000 tokens), mais améliore la qualité des actions → ROI positif |
| **Template breaking change** | Bas | Nouveaux paramètres sont optionnels (default None) |

---

## Métriques de succès (post-migration)

| Métrique | Avant | Objectif | Mesure |
|----------|-------|----------|--------|
| Actions pertinentes/review | ~1.2 | ≥2.0 | Logs review |
| Suggestions de liens | ~0.3 | ≥1.0 | Actions SUGGEST_LINKS |
| Détection doublons | 0 | ≥0.5 | Actions MERGE_INTO |
| Notes avec contexte enrichi | 0% | 80%+ | Logs context_loaded |
| **Alignement modèle PKM** | 0% | 90%+ | Notes avec pkm_model chargé |
| **Sections manquantes détectées** | 0 | ≥1.5/note | Actions STRUCTURE ciblant sections modèle |

---

## Estimation

- **11 commits atomiques** (9 + 4b + 4c)
- ~450 lignes ajoutées à retouche_reviewer.py
- ~60 lignes ajoutées à template_renderer.py
- ~150 lignes ajoutées à retouche_user.j2
- ~1000 lignes supprimées (note_reviewer.py)
- Bilan net : -340 lignes

---

## Améliorations futures (post-migration)

Ces améliorations peuvent être envisagées après la migration :

### 1. Contexte bidirectionnel (backlinks)

**Problème actuel** : On ne voit que les notes vers lesquelles cette note pointe, pas celles qui pointent vers elle.

**Solution** : Ajouter `incoming_links` à RetoucheContext.

```python
# Dans _load_context()
incoming_links = self._find_backlinks(note.title)
```

**Impact** : L'IA pourrait suggérer de consolider ou mettre à jour les notes qui référencent celle-ci.

### 2. Analyse temporelle des modifications

**Problème actuel** : On ne sait pas si une note "vieillit mal" (pas de modif depuis longtemps mais beaucoup de liens entrants récents).

**Solution** : Calculer un "stale score" basé sur :
- Dernière modification de la note
- Fréquence des références depuis d'autres notes modifiées récemment
- Événements calendrier passés liés

**Impact** : Détection proactive des notes nécessitant une mise à jour.

### 3. Contexte du Canevas personnalisé

**Problème actuel** : Le Canevas (Profile, Goals, Projects) est injecté dans les prompts emails mais pas dans Retouche.

**Solution** : Injecter le canevas pertinent selon le type de note.
- Note personne → Profile + Goals (pour contextualiser la relation)
- Note projet → Projects (pour voir où ça s'inscrit)

**Impact** : Actions plus alignées avec les objectifs de Johan.

### 4. Feedback loop sur les actions

**Problème actuel** : On ne sait pas quelles actions ont été réellement utiles pour Johan.

**Solution** : Tracker :
- Actions auto-apply acceptées (gardées) vs revertées
- Actions en Filage approuvées vs rejetées

**Impact** : Calibrer les seuils de confiance, améliorer le modèle d'actions.

### 5. Clustering de notes similaires

**Problème actuel** : On trouve des notes similaires une par une, mais on ne détecte pas les clusters de doublons.

**Solution** : Utiliser FAISS pour identifier des groupes de notes très proches (similarité > 0.9).

**Impact** : Proposer des merges groupés plutôt que unitaires.
