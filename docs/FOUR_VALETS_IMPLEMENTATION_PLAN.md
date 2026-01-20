# Plan d'implémentation — Architecture des Quatre Valets v3.0

**Date** : 2026-01-20
**Référence** : [FOUR_VALETS_SPEC.md](FOUR_VALETS_SPEC.md)
**Status** : Simplifié après analyse du codebase

---

## État de l'existant

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

### 🔧 Ce qui reste à faire

1. **Méthodes render spécifiques** dans `TemplateRenderer`
2. **Logique Four Valets** dans `MultiPassAnalyzer` (extension, pas remplacement)
3. **Configuration des seuils** dans `config/defaults.yaml`
4. **Tests spécifiques** pour le flux Four Valets

---

## Architecture : Sancho comme orchestrateur

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

## Phase 1 : Extension du TemplateRenderer

**Fichier** : `src/sancho/template_renderer.py`

**Tâches** :
- [ ] Ajouter `render_grimaud(event, max_content_chars, briefing)`
- [ ] Ajouter `render_bazin(event, previous_result, context, briefing)`
- [ ] Ajouter `render_planchet(event, previous_passes, context, briefing)`
- [ ] Ajouter `render_mousqueton(event, previous_passes, full_context, briefing)`

**Code** :
```python
# Dans TemplateRenderer

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
    context: StructuredContext,
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
    context: StructuredContext,
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
    full_context: StructuredContext,
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
```

---

## Phase 2 : Extension du MultiPassAnalyzer

**Fichier** : `src/sancho/multi_pass_analyzer.py`

**Approche** : Ajouter un mode `four_valets` à l'analyseur existant.

**Tâches** :
- [ ] Ajouter `_run_four_valets_pipeline()` comme alternative à `_run_passes()`
- [ ] Implémenter logique `early_stop` pour Grimaud
- [ ] Implémenter logique `needs_mousqueton` pour Planchet
- [ ] Ajouter `stopped_at` dans `MultiPassResult`

**Code** :
```python
# Dans MultiPassAnalyzer

async def analyze(
    self,
    event: PerceivedEvent,
    context: StructuredContext,
    use_four_valets: bool = True,  # v3.0 par défaut
) -> MultiPassResult:
    """Analyze event using Sancho's multi-pass pipeline."""
    if use_four_valets:
        return await self._run_four_valets_pipeline(event, context)
    return await self._run_legacy_pipeline(event, context)

async def _run_four_valets_pipeline(
    self,
    event: PerceivedEvent,
    context: StructuredContext,
) -> MultiPassResult:
    """Four Valets v3.0 pipeline."""
    passes: list[PassResult] = []

    # === GRIMAUD (Pass 1) ===
    grimaud = await self._run_grimaud(event)
    passes.append(grimaud)

    if self._should_early_stop(grimaud):
        return self._finalize(grimaud, passes, stopped_at="grimaud")

    # === BAZIN (Pass 2) ===
    bazin = await self._run_bazin(event, grimaud, context)
    passes.append(bazin)

    # === PLANCHET (Pass 3) ===
    planchet = await self._run_planchet(event, passes, context)
    passes.append(planchet)

    if self._planchet_can_conclude(planchet):
        return self._finalize(planchet, passes, stopped_at="planchet")

    # === MOUSQUETON (Pass 4) ===
    mousqueton = await self._run_mousqueton(event, passes, context)
    passes.append(mousqueton)

    return self._finalize(mousqueton, passes, stopped_at="mousqueton")

def _should_early_stop(self, result: PassResult) -> bool:
    """Grimaud early stop for ephemeral content."""
    return (
        result.raw.get("early_stop", False) and
        result.raw.get("action") == "delete" and
        result.confidence.overall > 0.95
    )

def _planchet_can_conclude(self, result: PassResult) -> bool:
    """Planchet stops if confidence > 90%."""
    return (
        not result.raw.get("needs_mousqueton", True) and
        result.confidence.overall > 0.90
    )
```

---

## Phase 3 : Configuration

**Fichier** : `config/defaults.yaml`

**Tâches** :
- [ ] Ajouter section `sancho.four_valets`

```yaml
sancho:
  # Architecture v3.0 - Four Valets
  four_valets:
    enabled: true

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
```

---

## Phase 4 : Tests

**Fichier** : `tests/unit/test_four_valets.py`

**Utilise** : Fixtures existantes de `conftest.py`

**Tâches** :
- [ ] Test `test_grimaud_early_stop_otp`
- [ ] Test `test_grimaud_early_stop_spam`
- [ ] Test `test_bazin_notes_filtering`
- [ ] Test `test_planchet_stops_high_confidence`
- [ ] Test `test_mousqueton_called_low_confidence`
- [ ] Test `test_full_pipeline_4_passes`

```python
import pytest
from unittest.mock import AsyncMock, patch

class TestFourValetsPipeline:
    """Tests for Four Valets v3.0 architecture."""

    @pytest.fixture
    def analyzer(self, mock_config):
        """MultiPassAnalyzer with mocked provider."""
        return MultiPassAnalyzer(
            provider=AsyncMock(),
            template_renderer=get_template_renderer(),
            context_searcher=AsyncMock(),
        )

    async def test_grimaud_early_stop_otp(self, analyzer):
        """Grimaud stops early on OTP codes."""
        event = create_event(
            subject="Code BoursoBank",
            content="Votre code: 123456. Valable 5 min.",
        )

        with patch_ai_response(grimaud_otp_response()):
            result = await analyzer.analyze(event, empty_context)

        assert result.stopped_at == "grimaud"
        assert result.action == "delete"
        assert result.passes_count == 1

    async def test_planchet_stops_high_confidence(self, analyzer):
        """Planchet concludes when confidence > 90%."""
        event = create_simple_business_event()

        with patch_ai_responses([
            grimaud_normal_response(),
            bazin_enriched_response(),
            planchet_confident_response(confidence=0.92),
        ]):
            result = await analyzer.analyze(event, rich_context)

        assert result.stopped_at == "planchet"
        assert result.passes_count == 3
        assert result.confidence.overall > 0.90
```

---

## Phase 5 : Validation

**Tâches** :
- [ ] Exécuter pipeline sur 100 emails de test
- [ ] Vérifier distribution des arrêts (Grimaud/Planchet/Mousqueton)
- [ ] Comparer coûts avec v2.2
- [ ] Valider qualité des extractions

**Métriques à surveiller** :
- `early_stop_rate` : % d'arrêts à Grimaud (cible: 15-25%)
- `planchet_stop_rate` : % d'arrêts à Planchet (cible: 60-70%)
- `mousqueton_rate` : % d'appels à Mousqueton (cible: 10-20%)
- `avg_cost_per_email` : Coût moyen (cible: < $0.015)

---

## Résumé des fichiers à modifier

| Fichier | Action | Priorité |
|---------|--------|----------|
| `src/sancho/template_renderer.py` | Ajouter 4 méthodes render | P0 |
| `src/sancho/multi_pass_analyzer.py` | Ajouter pipeline Four Valets | P0 |
| `config/defaults.yaml` | Ajouter section four_valets | P0 |
| `tests/unit/test_four_valets.py` | Créer tests | P1 |
| `docs/ARCHITECTURE.md` | Documenter v3.0 | P2 |

---

## Estimation

| Phase | Effort |
|-------|--------|
| Phase 1 : TemplateRenderer | ~2h |
| Phase 2 : MultiPassAnalyzer | ~4h |
| Phase 3 : Configuration | ~30min |
| Phase 4 : Tests | ~3h |
| Phase 5 : Validation | ~2h |
| **Total** | **~12h** |

---

## Checklist de lancement

- [ ] Templates v2 validés (Grimaud, Bazin, Planchet, Mousqueton)
- [ ] Méthodes render ajoutées
- [ ] Pipeline Four Valets implémenté
- [ ] Configuration en place
- [ ] Tests passent
- [ ] Validation sur dataset réel
- [ ] Documentation mise à jour
