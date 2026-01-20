# Plan d'implémentation — Architecture des Quatre Valets v3.0

**Date** : 2026-01-20
**Référence** : [FOUR_VALETS_SPEC.md](FOUR_VALETS_SPEC.md)
**Status** : Complet

---

## Table des matières

1. [État de l'existant](#1-état-de-lexistant)
2. [Architecture](#2-architecture--sancho-comme-orchestrateur)
3. [Phase 1 : Data Models](#3-phase-1--data-models)
4. [Phase 2 : TemplateRenderer](#4-phase-2--extension-du-templaterenderer)
5. [Phase 3 : MultiPassAnalyzer](#5-phase-3--extension-du-multipassanalyzer)
6. [Phase 4 : Configuration](#6-phase-4--configuration)
7. [Phase 5 : Parsing JSON](#7-phase-5--parsing-json)
8. [Phase 6 : Gestion des erreurs](#8-phase-6--gestion-des-erreurs)
9. [Phase 7 : Tests unitaires](#9-phase-7--tests-unitaires)
10. [Phase 8 : Tests E2E](#10-phase-8--tests-e2e)
11. [Phase 9 : Validation](#11-phase-9--validation)
12. [Phase 10 : Documentation](#12-phase-10--documentation)
13. [Résumé et estimation](#13-résumé-et-estimation)
14. [Checklist de lancement](#14-checklist-de-lancement)

---

## 1. État de l'existant

L'analyse du codebase révèle que **la majorité de l'infrastructure existe déjà**.

### ✅ Composants existants

| Composant | Fichier | Status |
|-----------|---------|--------|
| **Filtres Jinja2** | `src/sancho/template_renderer.py` | ✅ `truncate_smart`, `format_date`, `format_confidence` |
| **Configuration** | `config/defaults.yaml` | ✅ YAML + Pydantic + env vars |
| **Tests** | `tests/unit/conftest.py` | ✅ Fixtures avec mocks AI |
| **Provider Anthropic** | `src/sancho/providers/anthropic_provider.py` | ✅ Haiku/Sonnet/Opus |
| **Retrieval** | `src/passepartout/` | ✅ 5 niveaux (FAISS + embeddings + entity) |
| **Templates v2** | `templates/ai/v2/` | ✅ Grimaud, Bazin, Planchet, Mousqueton |
| **Multi-pass** | `src/sancho/multi_pass_analyzer.py` | ✅ Convergence + DecomposedConfidence |
| **PassResult** | `src/sancho/convergence.py` | ✅ Dataclass avec to_dict() |

### 🔧 Ce qui reste à faire

1. **Data models** : Ajouter `stopped_at`, `ValetType`, nouveaux `PassType`
2. **Méthodes render** : 4 nouvelles méthodes dans `TemplateRenderer`
3. **Pipeline Four Valets** : Extension de `MultiPassAnalyzer`
4. **Parsing JSON** : Nouveaux champs (early_stop, needs_mousqueton, notes_ignored, etc.)
5. **Configuration** : Section `sancho.four_valets` dans defaults.yaml
6. **Tests unitaires** : Tests spécifiques pour le flux Four Valets
7. **Tests E2E** : Tests d'intégration bout-en-bout
8. **Documentation** : Mise à jour ARCHITECTURE.md et user guide

---

## 2. Architecture : Sancho comme orchestrateur

```
┌─────────────────────────────────────────────────────────────┐
│                         SANCHO                               │
│              (Orchestrateur Multi-Pass)                      │
│                                                              │
│  src/sancho/multi_pass_analyzer.py                          │
│  ─────────────────────────────────                          │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              MODE: Four Valets v3.0                  │   │
│  │                                                      │   │
│  │  Grimaud → Bazin → Planchet → (Mousqueton?)         │   │
│  │     │                  │              │              │   │
│  │  early_stop?      toujours      confidence>90%?     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  Utilise:                                                   │
│  - TemplateRenderer (prompts)                               │
│  - AnthropicProvider (API Claude)                           │
│  - ContextSearcher (Passepartout)                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Phase 1 : Data Models

**Fichiers** : `src/sancho/convergence.py`, `src/sancho/multi_pass_analyzer.py`

### 3.1 Nouveaux types (convergence.py)

```python
from enum import Enum

class ValetType(str, Enum):
    """Type de valet dans l'architecture Four Valets."""
    GRIMAUD = "grimaud"      # Pass 1 - Extraction silencieuse
    BAZIN = "bazin"          # Pass 2 - Enrichissement contextuel
    PLANCHET = "planchet"    # Pass 3 - Critique et validation
    MOUSQUETON = "mousqueton"  # Pass 4 - Arbitrage final


class PassType(str, Enum):
    """Types de passes - étend l'existant."""
    # Legacy v2.2
    BLIND_EXTRACTION = "blind_extraction"
    CONTEXTUAL_REFINEMENT = "contextual_refinement"
    DEEP_REASONING = "deep_reasoning"
    EXPERT_ANALYSIS = "expert_analysis"

    # Four Valets v3.0
    GRIMAUD = "grimaud"
    BAZIN = "bazin"
    PLANCHET = "planchet"
    MOUSQUETON = "mousqueton"
```

### 3.2 Extension de PassResult (convergence.py)

```python
@dataclass
class PassResult:
    """Résultat d'une passe - version étendue pour Four Valets."""

    # Champs existants...
    pass_number: int
    pass_type: PassType
    # ...

    # Nouveaux champs Four Valets
    valet: Optional[ValetType] = None
    early_stop: bool = False
    early_stop_reason: Optional[str] = None
    needs_mousqueton: bool = True  # Default True, Planchet décide
    notes_used: list[str] = field(default_factory=list)
    notes_ignored: list[str] = field(default_factory=list)
    critique: Optional[dict] = None  # Planchet's critique
    arbitrage: Optional[dict] = None  # Mousqueton's arbitrage
```

### 3.3 Extension de MultiPassResult (multi_pass_analyzer.py)

```python
@dataclass
class MultiPassResult:
    """Résultat final - version étendue pour Four Valets."""

    # Champs existants...

    # Nouveau champ Four Valets
    stopped_at: Optional[str] = None  # "grimaud", "planchet", "mousqueton"

    @property
    def four_valets_mode(self) -> bool:
        """True si analysé avec Four Valets v3.0."""
        return self.stopped_at is not None
```

### 3.4 Tâches Phase 1

- [ ] Ajouter `ValetType` enum dans `convergence.py`
- [ ] Étendre `PassType` avec les 4 valets
- [ ] Ajouter les champs Four Valets à `PassResult`
- [ ] Ajouter `stopped_at` à `MultiPassResult`
- [ ] Mettre à jour `to_dict()` pour les deux classes

---

## 4. Phase 2 : Extension du TemplateRenderer

**Fichier** : `src/sancho/template_renderer.py`

### 4.1 Méthodes à ajouter

```python
def render_grimaud(
    self,
    event: PerceivedEvent,
    max_content_chars: int = 8000,
) -> str:
    """Render Grimaud (Pass 1) - Extraction silencieuse."""
    return self.render(
        "pass1_grimaud",
        event=event,
        now=datetime.now(),
        max_content_chars=max_content_chars,
        briefing=self._get_briefing(),
    )

def render_bazin(
    self,
    event: PerceivedEvent,
    previous_result: dict,
    context: Optional[StructuredContext],
    max_content_chars: int = 4000,
    max_context_notes: int = 5,
) -> str:
    """Render Bazin (Pass 2) - Enrichissement contextuel."""
    return self.render(
        "pass2_bazin",
        event=event,
        previous_result=previous_result,
        context=context,
        now=datetime.now(),
        max_content_chars=max_content_chars,
        max_context_notes=max_context_notes,
        briefing=self._get_briefing(),
    )

def render_planchet(
    self,
    event: PerceivedEvent,
    previous_passes: list[dict],
    context: Optional[StructuredContext],
    max_content_chars: int = 4000,
) -> str:
    """Render Planchet (Pass 3) - Critique et validation."""
    return self.render(
        "pass3_planchet",
        event=event,
        previous_passes=previous_passes,
        context=context,
        now=datetime.now(),
        max_content_chars=max_content_chars,
        briefing=self._get_briefing(),
    )

def render_mousqueton(
    self,
    event: PerceivedEvent,
    previous_passes: list[dict],
    full_context: Optional[StructuredContext],
) -> str:
    """Render Mousqueton (Pass 4) - Arbitrage final."""
    return self.render(
        "pass4_mousqueton",
        event=event,
        previous_passes=previous_passes,
        full_context=full_context,
        now=datetime.now(),
        briefing=self._get_briefing(),
    )

def _get_briefing(self) -> Optional[str]:
    """Récupère le briefing dynamique pour les valets."""
    return self._config.get("briefing_text") if self._config else None
```

### 4.2 Tâches Phase 2

- [ ] Ajouter `render_grimaud()`
- [ ] Ajouter `render_bazin()`
- [ ] Ajouter `render_planchet()`
- [ ] Ajouter `render_mousqueton()`
- [ ] Ajouter `_get_briefing()` helper

---

## 5. Phase 3 : Extension du MultiPassAnalyzer

**Fichier** : `src/sancho/multi_pass_analyzer.py`

### 5.1 Pipeline principal

```python
async def analyze(
    self,
    event: PerceivedEvent,
    sender_importance: str = "normal",
    use_four_valets: bool = True,
) -> MultiPassResult:
    """Analyze event using Sancho's multi-pass pipeline."""
    if use_four_valets and self.config.four_valets_enabled:
        return await self._run_four_valets_pipeline(event, sender_importance)
    return await self._run_legacy_pipeline(event, sender_importance)

async def _run_four_valets_pipeline(
    self,
    event: PerceivedEvent,
    sender_importance: str = "normal",
) -> MultiPassResult:
    """Four Valets v3.0 pipeline."""
    start_time = time.time()
    total_tokens = 0
    passes: list[PassResult] = []
    context: Optional[StructuredContext] = None

    # === GRIMAUD (Pass 1) ===
    grimaud = await self._run_grimaud(event)
    passes.append(grimaud)
    total_tokens += grimaud.tokens_used

    if self._should_early_stop(grimaud):
        return await self._finalize_four_valets(
            passes, event, start_time, total_tokens,
            stopped_at="grimaud",
            stop_reason=f"early_stop: {grimaud.early_stop_reason}",
        )

    # Get context for Bazin
    if self.context_searcher and grimaud.entities_discovered:
        context = await self.context_searcher.search_for_entities(
            list(grimaud.entities_discovered),
            sender_email=getattr(event, "from_person", None),
        )

    # === BAZIN (Pass 2) ===
    bazin = await self._run_bazin(event, grimaud, context)
    passes.append(bazin)
    total_tokens += bazin.tokens_used

    # === PLANCHET (Pass 3) ===
    planchet = await self._run_planchet(event, passes, context)
    passes.append(planchet)
    total_tokens += planchet.tokens_used

    if self._planchet_can_conclude(planchet):
        return await self._finalize_four_valets(
            passes, event, start_time, total_tokens,
            stopped_at="planchet",
            stop_reason=f"planchet_confident ({planchet.confidence.overall:.0%})",
            context=context,
        )

    # === MOUSQUETON (Pass 4) ===
    mousqueton = await self._run_mousqueton(event, passes, context)
    passes.append(mousqueton)
    total_tokens += mousqueton.tokens_used

    return await self._finalize_four_valets(
        passes, event, start_time, total_tokens,
        stopped_at="mousqueton",
        stop_reason="mousqueton_arbitrage",
        context=context,
    )
```

### 5.2 Helpers pour chaque valet

```python
async def _run_grimaud(self, event: PerceivedEvent) -> PassResult:
    """Exécute Grimaud (Pass 1) - Extraction silencieuse."""
    prompt = self.template_renderer.render_grimaud(
        event=event,
        max_content_chars=self.config.four_valets.grimaud_max_chars,
    )
    model_tier = self._get_valet_model("grimaud")
    api_params = self._get_valet_api_params("grimaud")

    result = await self._call_model(
        prompt=prompt,
        model_tier=model_tier,
        pass_number=1,
        pass_type=PassType.GRIMAUD,
        temperature=api_params.get("temperature", 0.1),
        max_tokens=api_params.get("max_tokens", 1500),
    )
    result.valet = ValetType.GRIMAUD
    return result

async def _run_bazin(
    self,
    event: PerceivedEvent,
    grimaud: PassResult,
    context: Optional[StructuredContext],
) -> PassResult:
    """Exécute Bazin (Pass 2) - Enrichissement contextuel."""
    prompt = self.template_renderer.render_bazin(
        event=event,
        previous_result=grimaud.to_dict(),
        context=context,
        max_content_chars=self.config.four_valets.bazin_max_chars,
        max_context_notes=self.config.four_valets.bazin_max_notes,
    )
    model_tier = self._get_valet_model("bazin")
    api_params = self._get_valet_api_params("bazin")

    result = await self._call_model(
        prompt=prompt,
        model_tier=model_tier,
        pass_number=2,
        pass_type=PassType.BAZIN,
        temperature=api_params.get("temperature", 0.2),
        max_tokens=api_params.get("max_tokens", 2000),
    )
    result.valet = ValetType.BAZIN
    return result

async def _run_planchet(
    self,
    event: PerceivedEvent,
    previous_passes: list[PassResult],
    context: Optional[StructuredContext],
) -> PassResult:
    """Exécute Planchet (Pass 3) - Critique et validation."""
    passes_dicts = [p.to_dict() for p in previous_passes]
    prompt = self.template_renderer.render_planchet(
        event=event,
        previous_passes=passes_dicts,
        context=context,
        max_content_chars=self.config.four_valets.planchet_max_chars,
    )
    model_tier = self._get_valet_model("planchet")
    api_params = self._get_valet_api_params("planchet")

    result = await self._call_model(
        prompt=prompt,
        model_tier=model_tier,
        pass_number=3,
        pass_type=PassType.PLANCHET,
        temperature=api_params.get("temperature", 0.3),
        max_tokens=api_params.get("max_tokens", 2000),
    )
    result.valet = ValetType.PLANCHET
    return result

async def _run_mousqueton(
    self,
    event: PerceivedEvent,
    previous_passes: list[PassResult],
    context: Optional[StructuredContext],
) -> PassResult:
    """Exécute Mousqueton (Pass 4) - Arbitrage final."""
    passes_dicts = [p.to_dict() for p in previous_passes]
    prompt = self.template_renderer.render_mousqueton(
        event=event,
        previous_passes=passes_dicts,
        full_context=context,
    )
    model_tier = self._get_valet_model("mousqueton")
    api_params = self._get_valet_api_params("mousqueton")

    result = await self._call_model(
        prompt=prompt,
        model_tier=model_tier,
        pass_number=4,
        pass_type=PassType.MOUSQUETON,
        temperature=api_params.get("temperature", 0.2),
        max_tokens=api_params.get("max_tokens", 2500),
    )
    result.valet = ValetType.MOUSQUETON
    return result
```

### 5.3 Helpers de décision

```python
def _should_early_stop(self, grimaud: PassResult) -> bool:
    """Vérifie si Grimaud demande un arrêt précoce."""
    threshold = self.config.four_valets.grimaud_early_stop_confidence
    return (
        grimaud.early_stop and
        grimaud.action == "delete" and
        grimaud.confidence.overall > threshold
    )

def _planchet_can_conclude(self, planchet: PassResult) -> bool:
    """Vérifie si Planchet peut conclure sans Mousqueton."""
    threshold = self.config.four_valets.planchet_stop_confidence
    return (
        not planchet.needs_mousqueton and
        planchet.confidence.overall > threshold
    )

def _get_valet_model(self, valet: str) -> ModelTier:
    """Récupère le modèle configuré pour un valet."""
    model_name = self.config.four_valets.models.get(valet, "haiku")
    return ModelTier(model_name)

def _get_valet_api_params(self, valet: str) -> dict:
    """Récupère les paramètres API pour un valet."""
    return self.config.four_valets.api_params.get(valet, {})
```

### 5.4 Tâches Phase 3

- [ ] Ajouter `use_four_valets` à `analyze()`
- [ ] Implémenter `_run_four_valets_pipeline()`
- [ ] Implémenter `_run_grimaud()`, `_run_bazin()`, `_run_planchet()`, `_run_mousqueton()`
- [ ] Implémenter `_should_early_stop()`, `_planchet_can_conclude()`
- [ ] Implémenter `_get_valet_model()`, `_get_valet_api_params()`
- [ ] Implémenter `_finalize_four_valets()`

---

## 6. Phase 4 : Configuration

**Fichier** : `config/defaults.yaml`

### 6.1 Section sancho.four_valets

```yaml
sancho:
  # Architecture v3.0 - Four Valets
  four_valets:
    enabled: true

    # Limites de contenu par valet
    grimaud_max_chars: 8000
    bazin_max_chars: 4000
    bazin_max_notes: 5
    planchet_max_chars: 4000

    # Seuils d'arrêt
    stopping_rules:
      grimaud_early_stop_confidence: 0.95
      planchet_stop_confidence: 0.90
      mousqueton_queue_confidence: 0.90

    # Modèles par valet
    models:
      grimaud: haiku
      bazin: haiku
      planchet: haiku
      mousqueton: sonnet

    # Paramètres API par valet
    api_params:
      grimaud:
        temperature: 0.1
        max_tokens: 1500
      bazin:
        temperature: 0.2
        max_tokens: 2000
      planchet:
        temperature: 0.3
        max_tokens: 2000
      mousqueton:
        temperature: 0.2
        max_tokens: 2500

    # Fallback vers legacy si erreur
    fallback_to_legacy: true
```

### 6.2 Schéma Pydantic

```python
# src/core/config_models.py

class FourValetsConfig(BaseModel):
    enabled: bool = True
    grimaud_max_chars: int = 8000
    bazin_max_chars: int = 4000
    bazin_max_notes: int = 5
    planchet_max_chars: int = 4000

    stopping_rules: dict = {
        "grimaud_early_stop_confidence": 0.95,
        "planchet_stop_confidence": 0.90,
    }
    models: dict = {
        "grimaud": "haiku",
        "bazin": "haiku",
        "planchet": "haiku",
        "mousqueton": "sonnet",
    }
    api_params: dict = {}
    fallback_to_legacy: bool = True
```

### 6.3 Tâches Phase 4

- [ ] Ajouter section `sancho.four_valets` à `defaults.yaml`
- [ ] Créer `FourValetsConfig` Pydantic model
- [ ] Intégrer dans `MultiPassConfig`

---

## 7. Phase 5 : Parsing JSON

**Fichier** : `src/sancho/multi_pass_analyzer.py`

### 7.1 Nouveaux champs à parser par valet

| Valet | Champs JSON à parser |
|-------|---------------------|
| **Grimaud** | `early_stop`, `early_stop_reason` |
| **Bazin** | `context_influence.notes_used`, `context_influence.notes_ignored`, `memory_hint` |
| **Planchet** | `critique`, `needs_mousqueton`, `changes_from_bazin`, `questions_for_mousqueton` |
| **Mousqueton** | `arbitrage.planchet_answers`, `arbitrage.conflicts_resolved`, `arbitrage.age_decision` |

### 7.2 Extension de _parse_response

```python
def _parse_response(self, response: str, ...) -> PassResult:
    # ... parsing JSON existant ...

    # Parse Four Valets specific fields
    early_stop = data.get("early_stop", False)
    early_stop_reason = data.get("early_stop_reason")
    needs_mousqueton = data.get("needs_mousqueton", True)

    # Parse context_influence (Bazin)
    context_influence = data.get("context_influence", {})
    notes_used = context_influence.get("notes_used", [])
    notes_ignored = context_influence.get("notes_ignored", [])

    # Parse critique (Planchet)
    critique = data.get("critique")

    # Parse arbitrage (Mousqueton)
    arbitrage = data.get("arbitrage")

    return PassResult(
        # ... existant ...
        early_stop=early_stop,
        early_stop_reason=early_stop_reason,
        needs_mousqueton=needs_mousqueton,
        notes_used=notes_used,
        notes_ignored=notes_ignored,
        critique=critique,
        arbitrage=arbitrage,
    )
```

### 7.3 Tâches Phase 5

- [ ] Parser `early_stop` et `early_stop_reason`
- [ ] Parser `context_influence` avec `notes_used`/`notes_ignored`
- [ ] Parser `critique` et `needs_mousqueton`
- [ ] Parser `arbitrage` structure
- [ ] Parser `memory_hint` structure

---

## 8. Phase 6 : Gestion des erreurs

### 8.1 Fallback vers legacy

```python
async def _run_four_valets_pipeline(self, event, sender_importance):
    """Pipeline avec fallback vers v2.2."""
    try:
        # ... pipeline normal ...
    except (APICallError, ParseError) as e:
        logger.error(f"Four Valets pipeline failed: {e}")
        if self.config.four_valets.fallback_to_legacy:
            logger.warning("Falling back to legacy v2.2 pipeline")
            return await self._run_legacy_pipeline(event, sender_importance)
        raise
```

### 8.2 Retry avec exponential backoff

```python
async def _run_valet_with_retry(
    self,
    valet_func: Callable,
    max_retries: int = 2,
    *args, **kwargs,
) -> PassResult:
    """Exécute un valet avec retry sur erreur."""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return await valet_func(*args, **kwargs)
        except (APICallError, ParseError) as e:
            last_error = e
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logger.warning(f"Valet failed (attempt {attempt + 1}), retrying in {wait_time}s")
                await asyncio.sleep(wait_time)
    raise last_error
```

### 8.3 Logging structuré

```python
def _log_valet_start(self, valet: str, event_id: str):
    logger.info(f"Four Valets: Starting {valet}", extra={
        "valet": valet, "event_id": event_id, "pipeline": "four_valets"
    })

def _log_valet_complete(self, valet: str, result: PassResult, event_id: str):
    logger.info(f"Four Valets: {valet} complete", extra={
        "valet": valet, "event_id": event_id,
        "confidence": result.confidence.overall,
        "extractions_count": len(result.extractions),
        "tokens": result.tokens_used,
    })
```

### 8.4 Tâches Phase 6

- [ ] Ajouter fallback vers legacy v2.2
- [ ] Ajouter retry avec exponential backoff
- [ ] Ajouter logging structuré par valet

---

## 9. Phase 7 : Tests unitaires

**Fichier** : `tests/unit/test_four_valets.py`

### 9.1 Fixtures

```python
@pytest.fixture
def mock_ai_router():
    """Mock AI router for tests."""
    return AsyncMock()

@pytest.fixture
def mock_context_searcher():
    """Mock context searcher."""
    searcher = AsyncMock()
    searcher.search_for_entities.return_value = create_mock_context()
    return searcher

@pytest.fixture
def analyzer(mock_ai_router, mock_context_searcher, mock_config):
    """MultiPassAnalyzer configured for Four Valets."""
    return MultiPassAnalyzer(
        ai_router=mock_ai_router,
        context_searcher=mock_context_searcher,
        config=mock_config,
    )

# Response helpers
def grimaud_otp_response() -> dict:
    return {
        "extractions": [],
        "action": "delete",
        "early_stop": True,
        "early_stop_reason": "otp",
        "confidence": {"entity_confidence": 0.99, ...},
    }

def planchet_confident_response(confidence: float = 0.92) -> dict:
    return {
        "extractions": [...],
        "action": "archive",
        "confidence": {"entity_confidence": confidence, ...},
        "needs_mousqueton": False,
    }
```

### 9.2 Tests unitaires

```python
class TestFourValetsPipeline:
    """Tests for Four Valets v3.0 architecture."""

    @pytest.mark.asyncio
    async def test_grimaud_early_stop_otp(self, analyzer):
        """Grimaud stops early on OTP codes."""
        event = create_event(subject="Code BoursoBank", content="Code: 123456")
        with patch_ai_response(grimaud_otp_response()):
            result = await analyzer.analyze(event)
        assert result.stopped_at == "grimaud"
        assert result.action == "delete"
        assert result.passes_count == 1

    @pytest.mark.asyncio
    async def test_grimaud_early_stop_spam(self, analyzer):
        """Grimaud stops early on spam."""
        event = create_event(subject="GAGNEZ 10000€", content="Cliquez ici...")
        with patch_ai_response(grimaud_spam_response()):
            result = await analyzer.analyze(event)
        assert result.stopped_at == "grimaud"

    @pytest.mark.asyncio
    async def test_bazin_notes_filtering(self, analyzer):
        """Bazin filters irrelevant notes."""
        event = create_event(...)
        with patch_ai_responses([grimaud_normal_response(), bazin_enriched_response(), planchet_confident_response()]):
            result = await analyzer.analyze(event)
        bazin_pass = result.pass_history[1]
        assert "Projet Alpha" in bazin_pass.notes_used
        assert any("hors sujet" in n for n in bazin_pass.notes_ignored)

    @pytest.mark.asyncio
    async def test_planchet_stops_high_confidence(self, analyzer):
        """Planchet concludes when confidence > 90%."""
        event = create_simple_business_event()
        with patch_ai_responses([grimaud_normal_response(), bazin_enriched_response(), planchet_confident_response(0.92)]):
            result = await analyzer.analyze(event)
        assert result.stopped_at == "planchet"
        assert result.passes_count == 3

    @pytest.mark.asyncio
    async def test_mousqueton_called_low_confidence(self, analyzer):
        """Mousqueton is called when Planchet has doubts."""
        event = create_complex_event()
        with patch_ai_responses([grimaud_normal_response(), bazin_enriched_response(), planchet_doubtful_response(), mousqueton_arbitrage_response()]):
            result = await analyzer.analyze(event)
        assert result.stopped_at == "mousqueton"
        assert result.passes_count == 4

    @pytest.mark.asyncio
    async def test_full_pipeline_4_passes(self, analyzer):
        """Complete pipeline with all 4 valets."""
        event = create_complex_event()
        with patch_ai_responses([grimaud_normal_response(), bazin_enriched_response(), planchet_doubtful_response(), mousqueton_arbitrage_response()]):
            result = await analyzer.analyze(event)
        valets = [p.valet for p in result.pass_history]
        assert valets == [ValetType.GRIMAUD, ValetType.BAZIN, ValetType.PLANCHET, ValetType.MOUSQUETON]

    @pytest.mark.asyncio
    async def test_legacy_fallback(self, analyzer):
        """Falls back to legacy v2.2 when Four Valets disabled."""
        analyzer.config.four_valets.enabled = False
        result = await analyzer.analyze(create_event(...))
        assert result.stopped_at is None
        assert result.four_valets_mode is False

    @pytest.mark.asyncio
    async def test_fallback_on_error(self, analyzer):
        """Falls back to legacy on API error."""
        with patch_ai_response(side_effect=APICallError("API error")):
            result = await analyzer.analyze(create_event(...))
        assert result.stopped_at is None  # Legacy mode
```

### 9.3 Tâches Phase 7

- [ ] Créer fixtures mock pour chaque valet
- [ ] Test `test_grimaud_early_stop_otp`
- [ ] Test `test_grimaud_early_stop_spam`
- [ ] Test `test_bazin_notes_filtering`
- [ ] Test `test_planchet_stops_high_confidence`
- [ ] Test `test_mousqueton_called_low_confidence`
- [ ] Test `test_full_pipeline_4_passes`
- [ ] Test `test_legacy_fallback`
- [ ] Test `test_fallback_on_error`

---

## 10. Phase 8 : Tests E2E

**Fichier** : `tests/e2e/test_four_valets_e2e.py`

### 10.1 Objectif

Tests d'intégration bout-en-bout avec vraies API (ou mocks réalistes) pour valider le flux complet.

### 10.2 Fixtures E2E

```python
import pytest
from pathlib import Path

@pytest.fixture
def real_analyzer():
    """Analyzer with real dependencies (or realistic mocks)."""
    from src.sancho.multi_pass_analyzer import create_multi_pass_analyzer
    from src.passepartout.context_searcher import ContextSearcher

    return create_multi_pass_analyzer(
        context_searcher=ContextSearcher(),
        enable_coherence_pass=True,
    )

@pytest.fixture
def test_emails_dir():
    """Directory containing test email fixtures."""
    return Path(__file__).parent / "fixtures" / "emails"

def load_email_fixture(filename: str) -> PerceivedEvent:
    """Load email from fixture file."""
    # ... load from JSON/YAML fixture
```

### 10.3 Tests E2E

```python
class TestFourValetsE2E:
    """End-to-end tests for Four Valets pipeline."""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_e2e_otp_email_full_flow(self, real_analyzer, test_emails_dir):
        """E2E: OTP email should be deleted after Grimaud only."""
        event = load_email_fixture("otp_boursobank.json")

        result = await real_analyzer.analyze(event)

        # Verify Grimaud early stop
        assert result.stopped_at == "grimaud"
        assert result.action == "delete"
        assert result.passes_count == 1
        assert result.total_tokens < 500  # Cost efficiency

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_e2e_business_email_with_context(self, real_analyzer, test_emails_dir):
        """E2E: Business email should use context and stop at Planchet."""
        event = load_email_fixture("business_meeting_invite.json")

        result = await real_analyzer.analyze(event)

        # Should have used context
        assert result.retrieved_context is not None
        assert len(result.pass_history) >= 2

        # Verify extractions
        assert len(result.extractions) > 0
        meeting_ext = next((e for e in result.extractions if e.type == "evenement"), None)
        assert meeting_ext is not None
        assert meeting_ext.calendar is True

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_e2e_complex_email_needs_mousqueton(self, real_analyzer, test_emails_dir):
        """E2E: Complex email with ambiguities should need Mousqueton."""
        event = load_email_fixture("complex_contract_negotiation.json")

        result = await real_analyzer.analyze(event)

        # Should need all 4 passes
        assert result.stopped_at == "mousqueton"
        assert result.passes_count == 4

        # Verify arbitrage was done
        mousqueton_pass = result.pass_history[-1]
        assert mousqueton_pass.arbitrage is not None

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_e2e_newsletter_detection(self, real_analyzer, test_emails_dir):
        """E2E: Newsletters should be deleted efficiently."""
        event = load_email_fixture("newsletter_techcrunch.json")

        result = await real_analyzer.analyze(event)

        assert result.action == "delete"
        # Should be detected early (Grimaud or Bazin)
        assert result.passes_count <= 2

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_e2e_context_influence_logged(self, real_analyzer, test_emails_dir):
        """E2E: Context influence should be tracked."""
        event = load_email_fixture("email_with_known_contact.json")

        result = await real_analyzer.analyze(event)

        # Verify context influence is captured
        assert result.context_influence is not None
        assert "notes_used" in result.context_influence
        assert len(result.context_influence["notes_used"]) > 0

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_e2e_memory_hint_for_passepartout(self, real_analyzer, test_emails_dir):
        """E2E: Extractions should have memory hints for Passepartout."""
        event = load_email_fixture("email_with_new_info.json")

        result = await real_analyzer.analyze(event)

        # At least one extraction should have memory_hint
        extractions_with_hints = [
            e for e in result.extractions
            if hasattr(e, "memory_hint") and e.memory_hint
        ]
        assert len(extractions_with_hints) > 0

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_e2e_coherence_pass_runs(self, real_analyzer, test_emails_dir):
        """E2E: Coherence pass should validate extractions."""
        event = load_email_fixture("email_targeting_existing_note.json")

        result = await real_analyzer.analyze(event)

        # Coherence pass should have run
        assert result.coherence_validated is True

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_e2e_batch_processing(self, real_analyzer, test_emails_dir):
        """E2E: Process batch of 10 emails and verify distribution."""
        emails = [
            load_email_fixture(f) for f in [
                "otp_boursobank.json",
                "newsletter_techcrunch.json",
                "business_meeting_invite.json",
                "simple_info_email.json",
                "complex_contract_negotiation.json",
                "spam_promo.json",
                "invoice_reminder.json",
                "calendar_update.json",
                "team_message.json",
                "support_ticket.json",
            ]
        ]

        results = []
        for email in emails:
            result = await real_analyzer.analyze(email)
            results.append(result)

        # Verify distribution
        stopped_at_counts = {"grimaud": 0, "planchet": 0, "mousqueton": 0}
        for r in results:
            stopped_at_counts[r.stopped_at] += 1

        # Expected: 20-30% Grimaud, 50-70% Planchet, 10-30% Mousqueton
        assert stopped_at_counts["grimaud"] >= 1  # At least OTP and spam
        assert stopped_at_counts["planchet"] >= 3  # Most business emails
```

### 10.4 Fixtures d'emails

Créer dans `tests/e2e/fixtures/emails/` :

| Fichier | Description | Attendu |
|---------|-------------|---------|
| `otp_boursobank.json` | Code OTP BoursoBank | Grimaud early_stop |
| `newsletter_techcrunch.json` | Newsletter TechCrunch | Delete rapide |
| `business_meeting_invite.json` | Invitation réunion projet | Planchet stop, extraction événement |
| `complex_contract_negotiation.json` | Négociation contrat complexe | Mousqueton arbitrage |
| `email_with_known_contact.json` | Email de contact connu | Context influence |
| `email_targeting_existing_note.json` | Email ciblant note existante | Coherence pass |
| `simple_info_email.json` | Email informatif simple | Planchet stop |
| `spam_promo.json` | Spam promotionnel | Grimaud delete |
| `invoice_reminder.json` | Rappel facture | Archive avec extraction |
| `calendar_update.json` | Mise à jour calendrier | Extraction événement |
| `team_message.json` | Message d'équipe | Archive simple |
| `support_ticket.json` | Ticket support | Extraction demande |

### 10.5 Tâches Phase 8

- [ ] Créer structure `tests/e2e/fixtures/emails/`
- [ ] Créer 12 fixtures d'emails de test
- [ ] Implémenter `load_email_fixture()`
- [ ] Test `test_e2e_otp_email_full_flow`
- [ ] Test `test_e2e_business_email_with_context`
- [ ] Test `test_e2e_complex_email_needs_mousqueton`
- [ ] Test `test_e2e_newsletter_detection`
- [ ] Test `test_e2e_context_influence_logged`
- [ ] Test `test_e2e_memory_hint_for_passepartout`
- [ ] Test `test_e2e_coherence_pass_runs`
- [ ] Test `test_e2e_batch_processing`

---

## 11. Phase 9 : Validation

### 11.1 Dataset de validation

Créer un dataset de 100 emails représentatifs :

| Catégorie | Quantité | Attendu |
|-----------|----------|---------|
| OTP/codes | 10 | Grimaud early_stop |
| Spam/promos | 10 | Grimaud early_stop |
| Business simple | 30 | Planchet stop |
| Business complexe | 20 | Planchet stop |
| Conflits/ambiguïtés | 15 | Mousqueton |
| Edge cases | 15 | Variable |

### 11.2 Métriques cibles

```yaml
metrics:
  # Distribution des arrêts
  early_stop_rate:
    target: 15-25%
    alert_if: "> 50%"

  planchet_stop_rate:
    target: 60-70%
    alert_if: "< 30%"

  mousqueton_rate:
    target: 10-20%
    alert_if: "> 40%"

  # Performance
  avg_cost_per_email:
    target: "< $0.015"

  avg_latency_ms:
    target: "< 5000ms"

  # Qualité
  extraction_accuracy:
    target: "> 90%"

  false_delete_rate:
    target: "< 1%"
```

### 11.3 Script de validation

```python
# scripts/validate_four_valets.py

async def validate_four_valets(dataset_path: str):
    """Run validation on test dataset."""
    results = {"total": 0, "stopped_at": {"grimaud": 0, "planchet": 0, "mousqueton": 0}}

    for email in load_dataset(dataset_path):
        result = await analyzer.analyze(email)
        results["total"] += 1
        results["stopped_at"][result.stopped_at] += 1

    total = results["total"]
    print(f"Early stop rate: {results['stopped_at']['grimaud'] / total:.1%}")
    print(f"Planchet stop rate: {results['stopped_at']['planchet'] / total:.1%}")
    print(f"Mousqueton rate: {results['stopped_at']['mousqueton'] / total:.1%}")
```

### 11.4 Tâches Phase 9

- [ ] Créer dataset de 100 emails
- [ ] Implémenter script de validation
- [ ] Exécuter validation
- [ ] Vérifier distribution des arrêts
- [ ] Comparer coûts avec v2.2
- [ ] Valider qualité des extractions

---

## 12. Phase 10 : Documentation

### 12.1 ARCHITECTURE.md

Mettre à jour avec :

```markdown
## Architecture d'analyse v3.0 - Four Valets

Scapin utilise une architecture d'analyse multi-passes appelée "Four Valets",
inspirée des valets des Trois Mousquetaires.

### Pipeline

```
Événement → Grimaud → Bazin → Planchet → (Mousqueton?)
               ↓          ↓          ↓
          early_stop?  toujours  confidence>90%?
```

### Les 4 valets

| Valet | Rôle | Modèle | Arrêt |
|-------|------|--------|-------|
| Grimaud | Extraction silencieuse | Haiku | OTP, spam (95%+) |
| Bazin | Enrichissement contextuel | Haiku | Jamais |
| Planchet | Critique et validation | Haiku | Confiance > 90% |
| Mousqueton | Arbitrage final | Sonnet | Toujours |

### Configuration

Voir `config/defaults.yaml` section `sancho.four_valets`.
```

### 12.2 User Guide

Créer `docs/user-guide/four-valets.md` :

```markdown
# Architecture Four Valets

## Vue d'ensemble

L'architecture Four Valets est le système d'analyse multi-passes de Scapin.
Elle utilise 4 "valets" (passes d'analyse) pour extraire et valider les
informations des emails.

## Comment ça marche

1. **Grimaud** (Pass 1) : Observe l'email sans contexte
   - Détecte les contenus éphémères (OTP, spam)
   - Peut arrêter l'analyse immédiatement

2. **Bazin** (Pass 2) : Enrichit avec les mémoires
   - Consulte les notes PKM
   - Identifie les entités connues

3. **Planchet** (Pass 3) : Critique et valide
   - Questionne les conclusions
   - Décide si Mousqueton est nécessaire

4. **Mousqueton** (Pass 4) : Arbitre final
   - Résout les conflits
   - Produit le verdict définitif

## Personnalisation

### Changer les seuils

Dans `config/defaults.yaml` :

```yaml
sancho:
  four_valets:
    stopping_rules:
      grimaud_early_stop_confidence: 0.95
      planchet_stop_confidence: 0.90
```

### Changer les modèles

```yaml
sancho:
  four_valets:
    models:
      grimaud: haiku
      bazin: haiku
      planchet: haiku
      mousqueton: sonnet  # Plus puissant pour l'arbitrage
```

## Monitoring

Vérifiez la distribution des arrêts :

- **Grimaud** : 15-25% (contenus éphémères)
- **Planchet** : 60-70% (cas standard)
- **Mousqueton** : 10-20% (cas complexes)
```

### 12.3 Tâches Phase 10

- [ ] Mettre à jour `ARCHITECTURE.md`
- [ ] Créer `docs/user-guide/four-valets.md`
- [ ] Mettre à jour `README.md` avec mention v3.0
- [ ] Ajouter exemples dans la documentation

---

## 13. Résumé et estimation

### 13.1 Fichiers à modifier

| Fichier | Action | Priorité | Effort |
|---------|--------|----------|--------|
| `src/sancho/convergence.py` | Ajouter `ValetType`, étendre `PassResult` | P0 | 1h |
| `src/sancho/multi_pass_analyzer.py` | Pipeline Four Valets complet | P0 | 4h |
| `src/sancho/template_renderer.py` | 4 méthodes render | P0 | 2h |
| `config/defaults.yaml` | Section `four_valets` | P0 | 30min |
| `src/core/config_models.py` | `FourValetsConfig` | P0 | 1h |
| `tests/unit/test_four_valets.py` | Tests unitaires | P1 | 3h |
| `tests/e2e/test_four_valets_e2e.py` | Tests E2E | P1 | 3h |
| `tests/e2e/fixtures/emails/` | Fixtures emails | P1 | 2h |
| `scripts/validate_four_valets.py` | Script validation | P2 | 1h |
| `docs/ARCHITECTURE.md` | Documentation v3.0 | P2 | 1h |
| `docs/user-guide/four-valets.md` | Guide utilisateur | P2 | 1h |

### 13.2 Estimation totale

| Phase | Effort |
|-------|--------|
| Phase 1 : Data Models | ~1h |
| Phase 2 : TemplateRenderer | ~2h |
| Phase 3 : MultiPassAnalyzer | ~4h |
| Phase 4 : Configuration | ~1.5h |
| Phase 5 : Parsing JSON | ~1h |
| Phase 6 : Gestion des erreurs | ~1h |
| Phase 7 : Tests unitaires | ~3h |
| Phase 8 : Tests E2E | ~5h |
| Phase 9 : Validation | ~2h |
| Phase 10 : Documentation | ~2h |
| **Total** | **~22.5h** |

---

## 14. Checklist de lancement

### Pré-requis
- [ ] Templates v2 validés (Grimaud, Bazin, Planchet, Mousqueton)
- [ ] Documentation spec complète (FOUR_VALETS_SPEC.md)

### Phase 1-2 : Data Models & Templates
- [ ] `ValetType` enum ajouté
- [ ] `PassType` étendu
- [ ] `PassResult` étendu avec champs Four Valets
- [ ] `MultiPassResult.stopped_at` ajouté
- [ ] 4 méthodes render implémentées

### Phase 3-6 : Core Implementation
- [ ] `_run_four_valets_pipeline()` implémenté
- [ ] Helpers `_run_grimaud/bazin/planchet/mousqueton` implémentés
- [ ] Logique d'arrêt implémentée
- [ ] Parsing JSON des nouveaux champs
- [ ] Fallback vers legacy v2.2
- [ ] Configuration dans defaults.yaml

### Phase 7-8 : Tests
- [ ] Tests unitaires passent (9 tests minimum)
- [ ] Tests E2E passent (8 tests minimum)
- [ ] Fixtures d'emails créées (12 minimum)

### Phase 9-10 : Validation & Docs
- [ ] Validation sur dataset 100 emails
- [ ] Métriques dans les cibles
- [ ] ARCHITECTURE.md mis à jour
- [ ] User guide créé

### Post-lancement
- [ ] Monitoring actif
- [ ] Anciens templates conservés (rollback possible)
- [ ] Feedback utilisateur collecté
