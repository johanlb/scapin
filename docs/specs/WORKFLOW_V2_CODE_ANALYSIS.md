# Analyse des Modifications de Code - Workflow v2

**Version** : 1.0
**Date** : 11 janvier 2026
**Référence** : [WORKFLOW_V2_SPEC.md](WORKFLOW_V2_SPEC.md)

---

## Vue d'Ensemble

Ce document identifie les modifications de code nécessaires pour implémenter le Workflow v2 "Knowledge Extraction", organisées par module.

### Légende

| Symbole | Signification |
|---------|---------------|
| 🆕 | Nouveau fichier à créer |
| ✏️ | Fichier existant à modifier |
| 📦 | Nouvelle dépendance |
| 🔴 | Effort important (>1 jour) |
| 🟡 | Effort moyen (4h-1 jour) |
| 🟢 | Effort faible (<4h) |

---

## 1. Nouvelles Dépendances

### 1.1 Python (requirements.txt / pyproject.toml)

```toml
# Phase 1 : Extraction locale
gliner = "^0.2.0"           # 📦 NER local (GLiNER)
setfit = "^1.0.0"           # 📦 Classification few-shot locale
onnxruntime = "^1.16.0"     # 📦 Inference optimisée (optionnel)

# Déjà présents mais à vérifier versions
sentence-transformers = "^2.2.0"  # Embeddings
faiss-cpu = "^1.7.4"              # Vector search
```

### 1.2 Effort

| Dépendance | Taille | Impact Mémoire | Effort Installation |
|------------|--------|----------------|---------------------|
| GLiNER | ~500MB | ~1GB RAM | 🟢 pip install |
| SetFit | ~200MB | ~500MB RAM | 🟢 pip install |
| ONNX Runtime | ~100MB | Variable | 🟡 Optionnel |

**Total RAM supplémentaire estimé** : ~1.5GB (acceptable pour M1 avec 16GB)

---

## 2. Module : src/trivelin/ (Perception)

### 2.1 Fichiers à Modifier

| Fichier | Type | Effort | Description |
|---------|------|--------|-------------|
| `processor.py` | ✏️ | 🟡 | Intégrer Phase 1 comme pré-traitement |
| `cognitive_pipeline.py` | ✏️ | 🔴 | Refactorer pour nouveau pipeline 6 phases |

### 2.2 Nouveaux Fichiers

| Fichier | Type | Effort | Description |
|---------|------|--------|-------------|
| `extractors/ner_extractor.py` | 🆕 | 🟡 | Wrapper GLiNER pour NER locale |
| `extractors/classifier.py` | 🆕 | 🟡 | Wrapper SetFit pour classification |
| `extractors/info_router.py` | 🆕 | 🟢 | Routing vers notes/OmniFocus |
| `fast_path.py` | 🆕 | 🟡 | Logique Fast Path (skip API) |

### 2.3 Détails processor.py

```python
# AVANT (v1)
class EmailProcessor:
    async def process_email(self, email: EmailMessage) -> ProcessingResult:
        perceived = self.perceive(email)
        if self.config.enable_cognitive_reasoning:
            result = await self.cognitive_pipeline.process(perceived)
        ...

# APRÈS (v2)
class EmailProcessor:
    async def process_email(self, email: EmailMessage) -> ProcessingResult:
        perceived = self.perceive(email)

        # Phase 1: Extraction locale (NOUVEAU)
        extracted = await self.extractor.extract(perceived)

        # Phase 2: Matching (NOUVEAU)
        matched = await self.matcher.match(extracted)

        # Fast Path check (NOUVEAU)
        if matched.can_fast_path:
            return await self.fast_path.execute(matched)

        # Phases 3-5: Pipeline complet
        result = await self.knowledge_pipeline.process(matched)
        ...
```

### 2.4 Nouveau fichier : extractors/ner_extractor.py

```python
# ~150 lignes
from gliner import GLiNER

class NERExtractor:
    """Extraction d'entités nommées avec GLiNER (local)"""

    LABELS = [
        "personne", "organisation", "projet",
        "lieu", "date", "montant", "email", "téléphone"
    ]

    def __init__(self, model_name: str = "urchade/gliner_multi-v2.1"):
        self.model = GLiNER.from_pretrained(model_name)

    def extract(self, text: str) -> list[Entity]:
        """Extrait les entités du texte"""
        predictions = self.model.predict_entities(text, self.LABELS)
        return [
            Entity(
                type=pred["label"],
                value=pred["text"],
                confidence=pred["score"],
                start=pred["start"],
                end=pred["end"]
            )
            for pred in predictions
        ]
```

---

## 3. Module : src/sancho/ (Raisonnement)

### 3.1 Fichiers à Modifier

| Fichier | Type | Effort | Description |
|---------|------|--------|-------------|
| `reasoning_engine.py` | ✏️ | 🔴 | Refactorer : 5 passes → 1 appel enrichi |
| `templates.py` | ✏️ | 🟡 | Ajouter template extraction_analysis |
| `router.py` | ✏️ | 🟢 | Ajuster pour nouveau format réponse |

### 3.2 Nouveaux Fichiers

| Fichier | Type | Effort | Description |
|---------|------|--------|-------------|
| `semantic_analyzer.py` | 🆕 | 🟡 | Phase 3 - Analyse sémantique unique |
| `templates/extraction_analysis.j2` | 🆕 | 🟡 | Template Jinja2 pour extraction |

### 3.3 Détails reasoning_engine.py

```python
# AVANT (v1) - Multi-pass
class ReasoningEngine:
    async def reason(self, wm: WorkingMemory) -> ReasoningResult:
        while wm.should_continue():  # Max 5 passes
            if pass_num == 1:
                result = await self._pass1_initial_analysis(wm)
            elif pass_num == 2:
                result = await self._pass2_context_enrichment(wm)
            # ... passes 3, 4, 5

# APRÈS (v2) - Single enriched call
class ReasoningEngine:
    async def reason(self, enriched_event: EnrichedEvent) -> AnalysisResult:
        """
        UN SEUL appel API avec tout le contexte pré-calculé
        """
        return await self.semantic_analyzer.analyze(enriched_event)
```

### 3.4 Impact

- **Suppression** : Logique multi-pass (500+ lignes)
- **Conservation** : Infrastructure prompt, JSON parsing, rate limiting
- **Migration** : Progressive avec feature flag

---

## 4. Module : src/passepartout/ (Connaissances)

### 4.1 Fichiers à Modifier

| Fichier | Type | Effort | Description |
|---------|------|--------|-------------|
| `note_manager.py` | ✏️ | 🟡 | Ajouter gestion liens bidirectionnels |
| `context_engine.py` | ✏️ | 🟡 | Optimiser pour matching Phase 2 |
| `vector_store.py` | ✏️ | 🟢 | Ajouter index entités (pas juste notes) |

### 4.2 Nouveaux Fichiers

| Fichier | Type | Effort | Description |
|---------|------|--------|-------------|
| `link_manager.py` | 🆕 | 🟡 | Gestion liens entre notes |
| `enricher.py` | 🆕 | 🔴 | Phase 4 - Enrichissement PKM |
| `maintenance/auto_linker.py` | 🆕 | 🟡 | Phase 6 - Linking automatique |
| `maintenance/similarity_checker.py` | 🆕 | 🟡 | Phase 6 - Détection doublons |
| `maintenance/synthesizer.py` | 🆕 | 🟡 | Phase 6 - Génération synthèses |
| `maintenance/cleaner.py` | 🆕 | 🟢 | Phase 6 - Nettoyage |

### 4.3 Détails note_manager.py

```python
# AJOUTS (v2)
class NoteManager:
    # ... méthodes existantes ...

    # NOUVEAU : Gestion des liens
    async def add_link(
        self,
        source_id: str,
        target_id: str,
        relation: str
    ) -> bool:
        """Crée un lien bidirectionnel entre deux notes"""
        ...

    async def get_incoming_links(self, note_id: str) -> list[NoteLink]:
        """Récupère les liens entrants vers une note"""
        ...

    async def get_outgoing_links(self, note_id: str) -> list[NoteLink]:
        """Récupère les liens sortants d'une note"""
        ...

    # NOUVEAU : Enrichissement structuré
    async def enrich_note(
        self,
        note_id: str,
        section: str,
        content: str,
        source: str
    ) -> bool:
        """Ajoute du contenu dans une section spécifique"""
        ...
```

### 4.4 Nouveau format Note (frontmatter)

```yaml
# AVANT (v1)
---
id: note_xxx
title: Marc Dupont
type: personne
tags: [equipe]
---

# APRÈS (v2)
---
id: note_xxx
title: Marc Dupont
type: personne
tags: [equipe]
links:
  outgoing:
    - target: Projet Alpha
      relation: travaille_sur
      since: 2026-01-05
  incoming:
    - source: Réunion Budget
      relation: participant
---
```

---

## 5. Module : src/sganarelle/ (Apprentissage)

### 5.1 Fichiers à Modifier

| Fichier | Type | Effort | Description |
|---------|------|--------|-------------|
| `pattern_store.py` | ✏️ | 🟡 | Étendre pour Fast Path patterns |
| `learning_engine.py` | ✏️ | 🟢 | Adapter au nouveau format feedback |

### 5.2 Nouveaux Fichiers

| Fichier | Type | Effort | Description |
|---------|------|--------|-------------|
| `fast_path_learner.py` | 🆕 | 🟡 | Apprentissage patterns Fast Path |

### 5.3 Détails pattern_store.py

```python
# AJOUTS (v2)
class PatternStore:
    # ... méthodes existantes ...

    # NOUVEAU : Patterns pour Fast Path
    def get_fast_path_pattern(
        self,
        sender: str,
        subject: str
    ) -> Optional[FastPathPattern]:
        """Trouve un pattern Fast Path applicable"""
        ...

    def learn_fast_path(
        self,
        event: PerceivedEvent,
        action: EventAction,
        success: bool
    ) -> None:
        """Apprend un nouveau pattern Fast Path"""
        ...
```

---

## 6. Module : src/figaro/ (Exécution)

### 6.1 Fichiers à Modifier

| Fichier | Type | Effort | Description |
|---------|------|--------|-------------|
| `orchestrator.py` | ✏️ | 🟡 | Adapter pour Phase 5 actions |
| `actions/notes.py` | ✏️ | 🟢 | Ajouter actions enrichissement |

### 6.2 Nouveaux Fichiers

| Fichier | Type | Effort | Description |
|---------|------|--------|-------------|
| `actions/omnifocus.py` | 🆕 | 🟡 | Actions OmniFocus (AppleScript) |
| `actions/links.py` | 🆕 | 🟢 | Actions création liens |

---

## 7. Module : src/integrations/ (Intégrations)

### 7.1 Nouveaux Fichiers

| Fichier | Type | Effort | Description |
|---------|------|--------|-------------|
| `apple/omnifocus_client.py` | 🆕 | 🟡 | Client OmniFocus (AppleScript) |
| `apple/omnifocus_models.py` | 🆕 | 🟢 | Modèles OmniFocus |

### 7.2 Détails omnifocus_client.py

```python
# ~200 lignes
class OmniFocusClient:
    """Client pour OmniFocus via AppleScript"""

    async def create_task(
        self,
        title: str,
        project: Optional[str] = None,
        due_date: Optional[datetime] = None,
        defer_date: Optional[datetime] = None,
        note: Optional[str] = None,
        tags: list[str] = []
    ) -> str:
        """Crée une tâche et retourne son ID"""
        script = self._build_create_script(...)
        return await self._execute_applescript(script)

    async def complete_task(self, task_id: str) -> bool:
        """Marque une tâche comme complète"""
        ...
```

---

## 8. Module : src/core/ (Noyau)

### 8.1 Nouveaux Fichiers

| Fichier | Type | Effort | Description |
|---------|------|--------|-------------|
| `models/v2_models.py` | 🆕 | 🟡 | Nouveaux modèles de données v2 |
| `pipeline/knowledge_pipeline.py` | 🆕 | 🔴 | Orchestrateur pipeline 6 phases |

### 8.2 Détails v2_models.py

```python
# ~300 lignes - Tous les nouveaux modèles

@dataclass
class ExtractedEvent:
    """Sortie Phase 1"""
    event: PerceivedEvent
    entities: list[Entity]
    info_type: str
    info_type_confidence: float
    embedding: np.ndarray
    extraction_time_ms: float

@dataclass
class EnrichedEvent:
    """Sortie Phase 2"""
    phase1: ExtractedEvent
    matched_notes: list[MatchedNote]
    matched_patterns: list[MatchedPattern]
    context: ContextBundle
    can_fast_path: bool
    fast_path_action: Optional[EventAction]

@dataclass
class AnalysisResult:
    """Sortie Phase 3"""
    informations: list[ExtractedInfo]
    liens_detectes: list[NoteLink]
    action_evenement: EventAction
    resume: str
    api_usage: dict

@dataclass
class EnrichmentResult:
    """Sortie Phase 4"""
    notes_created: list[str]
    notes_updated: list[str]
    links_created: list[NoteLink]
    tasks_created: list[str]
    queued_items: list[QueueItem]

# ... autres modèles
```

---

## 9. Module : src/jeeves/api/ (API)

### 9.1 Fichiers à Modifier

| Fichier | Type | Effort | Description |
|---------|------|--------|-------------|
| `routers/queue.py` | ✏️ | 🟢 | Adapter pour nouveaux types queue |
| `services/queue_service.py` | ✏️ | 🟢 | Adapter pour enrichissement items |

### 9.2 Nouveaux Fichiers

| Fichier | Type | Effort | Description |
|---------|------|--------|-------------|
| `routers/maintenance.py` | 🆕 | 🟢 | Endpoints maintenance PKM |
| `routers/links.py` | 🆕 | 🟢 | Endpoints gestion liens |

---

## 10. Configuration

### 10.1 Fichiers à Modifier

| Fichier | Type | Effort | Description |
|---------|------|--------|-------------|
| `src/core/config_manager.py` | ✏️ | 🟡 | Ajouter config Workflow v2 |

### 10.2 Nouvelles Variables

```python
# Dans config_manager.py

class WorkflowV2Config(BaseModel):
    """Configuration Workflow v2"""

    # Feature flags
    enabled: bool = False
    fast_path_enabled: bool = True

    # Phase 1
    ner_model: str = "urchade/gliner_multi-v2.1"
    classifier_model: str = "setfit/distilbert-base-sst2"

    # Phase 2
    entity_match_threshold: float = 0.85
    fast_path_confidence_threshold: float = 0.90

    # Phase 4
    auto_apply_note_threshold: float = 0.90
    auto_apply_link_threshold: float = 0.85
    auto_apply_task_threshold: float = 0.88

    # Phase 6
    maintenance_enabled: bool = True
    linking_interval_hours: int = 1
    similarity_check_daily: bool = True
```

---

## 11. Tests

### 11.1 Nouveaux Fichiers de Test

| Fichier | Type | Effort | Description |
|---------|------|--------|-------------|
| `tests/unit/test_ner_extractor.py` | 🆕 | 🟢 | Tests extraction NER |
| `tests/unit/test_classifier.py` | 🆕 | 🟢 | Tests classification |
| `tests/unit/test_fast_path.py` | 🆕 | 🟡 | Tests Fast Path |
| `tests/unit/test_link_manager.py` | 🆕 | 🟡 | Tests gestion liens |
| `tests/unit/test_enricher.py` | 🆕 | 🟡 | Tests enrichissement |
| `tests/integration/test_v2_pipeline.py` | 🆕 | 🔴 | Tests pipeline complet |

---

## 12. Résumé des Efforts

### 12.1 Par Module

| Module | Nouveaux Fichiers | Fichiers Modifiés | Effort Total |
|--------|-------------------|-------------------|--------------|
| **trivelin** | 4 | 2 | 🔴 ~3-4 jours |
| **sancho** | 2 | 3 | 🔴 ~2-3 jours |
| **passepartout** | 6 | 3 | 🔴 ~4-5 jours |
| **sganarelle** | 1 | 2 | 🟡 ~1 jour |
| **figaro** | 2 | 2 | 🟡 ~1-2 jours |
| **integrations** | 2 | 0 | 🟡 ~1 jour |
| **core** | 2 | 0 | 🔴 ~2 jours |
| **jeeves/api** | 2 | 2 | 🟢 ~0.5 jour |
| **config** | 0 | 1 | 🟢 ~0.5 jour |
| **tests** | 6 | — | 🔴 ~3 jours |
| **TOTAL** | **27** | **15** | **~18-22 jours** |

### 12.2 Par Phase Pipeline

| Phase | Nouveaux Fichiers | Effort |
|-------|-------------------|--------|
| Phase 1 (Extraction) | 4 | 🔴 ~3 jours |
| Phase 2 (Matching) | 2 | 🟡 ~2 jours |
| Phase 3 (Analyse) | 2 | 🟡 ~2 jours |
| Phase 4 (Enrichissement) | 3 | 🔴 ~3 jours |
| Phase 5 (Action) | 2 | 🟡 ~1 jour |
| Phase 6 (Maintenance) | 4 | 🔴 ~3 jours |
| Infrastructure | 10 | 🔴 ~6 jours |

---

## 13. Ordre de Migration Recommandé

### Phase A : Infrastructure (Semaine 1-2)

1. ✅ Ajouter dépendances (GLiNER, SetFit)
2. ✅ Créer `core/models/v2_models.py`
3. ✅ Créer `core/config_manager.py` (WorkflowV2Config)
4. ✅ Feature flag `WORKFLOW_V2_ENABLED=false`

### Phase B : Extraction Locale (Semaine 2-3)

5. ✅ Créer `trivelin/extractors/ner_extractor.py`
6. ✅ Créer `trivelin/extractors/classifier.py`
7. ✅ Tests unitaires extracteurs
8. ✅ Intégrer dans `processor.py` (optionnel via flag)

### Phase C : Fast Path (Semaine 3-4)

9. ✅ Créer `trivelin/fast_path.py`
10. ✅ Étendre `sganarelle/pattern_store.py`
11. ✅ Tests Fast Path
12. ✅ Activer Fast Path (mesurer impact)

### Phase D : Pipeline Complet (Semaine 4-6)

13. ✅ Créer `sancho/semantic_analyzer.py`
14. ✅ Créer `passepartout/link_manager.py`
15. ✅ Créer `passepartout/enricher.py`
16. ✅ Créer `core/pipeline/knowledge_pipeline.py`
17. ✅ Tests intégration pipeline

### Phase E : Maintenance (Semaine 6-7)

18. ✅ Créer modules `passepartout/maintenance/`
19. ✅ Scheduler maintenance
20. ✅ Tests maintenance

### Phase F : Migration Complète (Semaine 7-8)

21. ✅ Deprecate v1 pipeline
22. ✅ `WORKFLOW_V2_ENABLED=true` par défaut
23. ✅ Monitoring et ajustements

---

## 14. Risques Identifiés

| Risque | Impact | Mitigation |
|--------|--------|------------|
| GLiNER/SetFit RAM élevé | Performance M1 | Lazy loading, modèles plus petits |
| Incompatibilité format notes | Perte données | Migration progressive, backup Git |
| Fast Path faux positifs | Perte info | Seuil conservateur (95%), review |
| OmniFocus permissions | Fonctionnalité | Fallback queue manuelle |
| Tests insuffisants | Régression | Coverage 90%+ avant migration |

---

## 15. Priorisation : Quick Wins vs Deep Refactoring

### 15.1 Quick Wins (1-2 jours chacun, valeur immédiate)

Ces changements peuvent être implémentés rapidement et apportent une valeur immédiate :

| # | Changement | Effort | Valeur | Justification |
|---|------------|--------|--------|---------------|
| **QW1** | Configuration WorkflowV2Config | 🟢 0.5j | Haute | Base pour tout le reste, feature flags |
| **QW2** | Modèles v2 (`core/models/v2_models.py`) | 🟢 1j | Haute | Fondation des types, pas de refactoring |
| **QW3** | NER Extractor wrapper GLiNER | 🟢 1j | Haute | Extraction entités sans modifier pipeline |
| **QW4** | Template extraction_analysis.j2 | 🟢 0.5j | Haute | Prompt optimisé, utilisable standalone |
| **QW5** | OmniFocus client AppleScript | 🟡 1j | Moyenne | Indépendant, utile hors v2 aussi |
| **QW6** | Link manager basique | 🟡 1j | Moyenne | Gestion liens sans changer format notes |

**Total Quick Wins** : ~5-6 jours
**Valeur** : Infrastructure prête, composants réutilisables, risque minimal

### 15.2 Medium Effort (3-5 jours chacun)

Ces changements nécessitent plus d'effort mais restent modulaires :

| # | Changement | Effort | Valeur | Dépendances |
|---|------------|--------|--------|-------------|
| **ME1** | Fast Path complet | 🟡 3j | Très haute | QW1, QW3, patterns Sganarelle |
| **ME2** | Classifier SetFit | 🟡 2j | Haute | QW1 |
| **ME3** | Semantic Analyzer (Phase 3) | 🟡 3j | Haute | QW4 |
| **ME4** | Enricher PKM (Phase 4) | 🟡 4j | Très haute | QW6, ME3 |
| **ME5** | API endpoints maintenance | 🟡 2j | Moyenne | QW6 |

**Total Medium Effort** : ~14 jours
**Valeur** : Fonctionnalités clés du workflow v2

### 15.3 Deep Refactoring (1+ semaine chacun)

Ces changements nécessitent une restructuration significative :

| # | Changement | Effort | Valeur | Risque |
|---|------------|--------|--------|--------|
| **DR1** | Refactoring cognitive_pipeline.py | 🔴 5j | Critique | Haut - cœur du système |
| **DR2** | Refactoring reasoning_engine.py | 🔴 4j | Critique | Haut - suppression multi-pass |
| **DR3** | Format notes avec liens bidirectionnels | 🔴 3j | Haute | Moyen - migration données |
| **DR4** | Knowledge pipeline orchestrateur | 🔴 5j | Critique | Haut - nouvelle architecture |
| **DR5** | Maintenance PKM (Phase 6) | 🔴 5j | Moyenne | Moyen - nouveau système |

**Total Deep Refactoring** : ~22 jours
**Valeur** : Architecture v2 complète

### 15.4 Ordre d'Implémentation Recommandé

```
SEMAINE 1-2: Quick Wins
┌────────────────────────────────────────────────────────────────┐
│  QW1 → QW2 → QW3 → QW4 → QW5 → QW6                            │
│  (Config) (Models) (NER) (Template) (OmniFocus) (Links)        │
│                                                                 │
│  Résultat: Composants standalone prêts, 0 régression           │
└────────────────────────────────────────────────────────────────┘
                              ↓
SEMAINE 3-4: Fast Path (Valeur Immédiate)
┌────────────────────────────────────────────────────────────────┐
│  ME1 (Fast Path) + ME2 (Classifier)                            │
│                                                                 │
│  Résultat: 40% des emails traités sans API = -40% coûts        │
│  Feature flag: FAST_PATH_ENABLED=true                          │
└────────────────────────────────────────────────────────────────┘
                              ↓
SEMAINE 5-6: Analyse Sémantique v2
┌────────────────────────────────────────────────────────────────┐
│  ME3 (Semantic Analyzer) + QW4 amélioré                        │
│                                                                 │
│  Résultat: 1 appel API vs 3-5 = -60% coûts supplémentaires     │
│  Feature flag: SEMANTIC_V2_ENABLED=true                         │
└────────────────────────────────────────────────────────────────┘
                              ↓
SEMAINE 7-8: Enrichissement PKM
┌────────────────────────────────────────────────────────────────┐
│  DR3 (Format notes) + ME4 (Enricher) + QW6 étendu              │
│                                                                 │
│  Résultat: PKM avec liens bidirectionnels, enrichissement auto │
│  Migration notes existantes (script)                           │
└────────────────────────────────────────────────────────────────┘
                              ↓
SEMAINE 9-10: Pipeline Complet
┌────────────────────────────────────────────────────────────────┐
│  DR1 + DR2 + DR4 (Refactoring majeur)                          │
│                                                                 │
│  Résultat: Architecture v2 complète                            │
│  WORKFLOW_V2_ENABLED=true par défaut                           │
└────────────────────────────────────────────────────────────────┘
                              ↓
SEMAINE 11-12: Maintenance & Polish
┌────────────────────────────────────────────────────────────────┐
│  DR5 (Maintenance) + ME5 (API) + Tests finaux                  │
│                                                                 │
│  Résultat: Système complet avec auto-amélioration              │
│  Deprecation v1, monitoring production                         │
└────────────────────────────────────────────────────────────────┘
```

### 15.5 Jalons Intermédiaires avec Valeur Mesurable

| Jalon | Semaine | Valeur Mesurable | KPI |
|-------|---------|------------------|-----|
| **M1: Fast Path MVP** | S4 | -40% appels API | Coût/email |
| **M2: Analyse v2** | S6 | -70% appels API total | Coût/email |
| **M3: PKM Neural** | S8 | +50% liens entre notes | Liens/semaine |
| **M4: v2 Complet** | S10 | Workflow v2 par défaut | Temps/email |
| **M5: Auto-amélioration** | S12 | Maintenance autonome | Qualité PKM |

### 15.6 Plan d'Action Immédiat (Prochaine Session)

**Objectif** : Implémenter QW1 + QW2 (fondations)

1. **QW1** : Ajouter `WorkflowV2Config` dans `config_manager.py`
   - Variables : `enabled`, `fast_path_enabled`, seuils
   - Tests unitaires

2. **QW2** : Créer `src/core/models/v2_models.py`
   - Dataclasses : `ExtractedEvent`, `EnrichedEvent`, `AnalysisResult`, etc.
   - Tests unitaires

3. **Bonus si temps** : Ajouter dépendances GLiNER/SetFit dans `pyproject.toml`

**Critères de succès** :
- [ ] Configuration v2 loadable
- [ ] Modèles typés et validés
- [ ] Tests passent
- [ ] Aucune régression sur v1

---

*Document généré le 11 janvier 2026*
