# Plan d'implémentation — Architecture des Quatre Valets

**Date** : 2026-01-20
**Référence** : [FOUR_VALETS_SPEC.md](FOUR_VALETS_SPEC.md)

---

## Phase 1 : Préparation (Foundation)

### 1.1 Mise à jour du TemplateRenderer

**Fichier** : `src/sancho/template_renderer.py`

**Tâches** :
- [ ] Ajouter méthodes `render_grimaud()`, `render_bazin()`, `render_planchet()`, `render_mousqueton()`
- [ ] Conserver les anciennes méthodes `render_pass1()`, `render_pass2()`, `render_pass4()` pour rollback
- [ ] Ajouter paramètre `version="v3"` pour switch entre architectures

**Code suggéré** :
```python
def render_grimaud(self, event: Any, max_content_chars: int = 8000) -> str:
    """Render Pass 1 (Grimaud) template."""
    return self.render("pass1_grimaud", event=event, max_content_chars=max_content_chars)

def render_bazin(
    self,
    event: Any,
    previous_result: dict,
    context: Any,
    max_content_chars: int = 8000,
    max_context_notes: int = 5,
) -> str:
    """Render Pass 2 (Bazin) template."""
    return self.render(
        "pass2_bazin",
        event=event,
        previous_result=previous_result,
        context=context,
        max_content_chars=max_content_chars,
        max_context_notes=max_context_notes,
    )

def render_planchet(
    self,
    event: Any,
    previous_passes: list[dict],
    context: Any,
    max_content_chars: int = 8000,
) -> str:
    """Render Pass 3 (Planchet) template."""
    return self.render(
        "pass3_planchet",
        event=event,
        previous_passes=previous_passes,
        context=context,
        max_content_chars=max_content_chars,
    )

def render_mousqueton(
    self,
    event: Any,
    previous_passes: list[dict],
    full_context: Any,
) -> str:
    """Render Pass 4 (Mousqueton) template."""
    return self.render(
        "pass4_mousqueton",
        event=event,
        previous_passes=previous_passes,
        full_context=full_context,
    )
```

### 1.2 Création du FourValetsAnalyzer

**Fichier** : `src/sancho/four_valets_analyzer.py` (nouveau)

**Tâches** :
- [ ] Créer classe `FourValetsAnalyzer`
- [ ] Implémenter logique d'arrêt précoce
- [ ] Implémenter sélection de modèle adaptative
- [ ] Ajouter métriques de suivi

**Structure suggérée** :
```python
class FourValetsAnalyzer:
    """
    Multi-pass analyzer using the Four Valets architecture.

    Flow:
        Grimaud → (early_stop?) → Bazin → Planchet → (confidence>90%?) → Mousqueton
    """

    def __init__(
        self,
        template_renderer: TemplateRenderer,
        provider: AIProvider,
        model_selector: ModelSelector,
    ):
        self._renderer = template_renderer
        self._provider = provider
        self._model_selector = model_selector

    async def analyze(self, event: PerceivedEvent, context: StructuredContext) -> AnalysisResult:
        """Run the Four Valets analysis pipeline."""
        passes = []

        # Pass 1: Grimaud
        grimaud_result = await self._run_grimaud(event)
        passes.append(grimaud_result)

        if self._should_early_stop(grimaud_result):
            return self._finalize(grimaud_result, passes, stopped_at="grimaud")

        # Pass 2: Bazin
        bazin_result = await self._run_bazin(event, grimaud_result, context)
        passes.append(bazin_result)

        # Pass 3: Planchet (always runs after Bazin)
        planchet_result = await self._run_planchet(event, passes, context)
        passes.append(planchet_result)

        if self._planchet_can_conclude(planchet_result):
            return self._finalize(planchet_result, passes, stopped_at="planchet")

        # Pass 4: Mousqueton
        mousqueton_result = await self._run_mousqueton(event, passes, context)
        passes.append(mousqueton_result)

        return self._finalize(mousqueton_result, passes, stopped_at="mousqueton")

    def _should_early_stop(self, result: dict) -> bool:
        """Check if Grimaud triggered early stop."""
        return (
            result.get("early_stop", False) and
            result.get("action") == "delete" and
            result.get("confidence", {}).get("overall", 0) > 0.95
        )

    def _planchet_can_conclude(self, result: dict) -> bool:
        """Check if Planchet's confidence allows stopping."""
        return (
            not result.get("needs_mousqueton", True) and
            result.get("confidence", {}).get("overall", 0) > 0.90
        )
```

### 1.3 Mise à jour des types

**Fichier** : `src/sancho/types.py` (ou créer si inexistant)

**Tâches** :
- [ ] Ajouter `ValetResult` TypedDict pour chaque valet
- [ ] Ajouter `FourValetsConfig` pour configuration
- [ ] Ajouter enums pour `EarlyStopReason`, `StoppedAt`

---

## Phase 2 : Intégration

### 2.1 Intégration avec MultiPassAnalyzer existant

**Fichier** : `src/sancho/multi_pass_analyzer.py`

**Tâches** :
- [ ] Ajouter flag `use_four_valets: bool = False`
- [ ] Router vers `FourValetsAnalyzer` si flag actif
- [ ] Conserver comportement v2.2 par défaut

**Code suggéré** :
```python
class MultiPassAnalyzer:
    def __init__(self, ..., use_four_valets: bool = False):
        self._use_four_valets = use_four_valets
        if use_four_valets:
            self._four_valets = FourValetsAnalyzer(...)

    async def analyze(self, event, context):
        if self._use_four_valets:
            return await self._four_valets.analyze(event, context)
        return await self._legacy_analyze(event, context)
```

### 2.2 Configuration

**Fichier** : `config/sancho.yaml` (ou équivalent)

**Tâches** :
- [ ] Ajouter section `four_valets`
- [ ] Configurer seuils d'arrêt
- [ ] Configurer sélection de modèle

**Structure suggérée** :
```yaml
sancho:
  four_valets:
    enabled: false  # Activer en Phase 3

    stopping_rules:
      grimaud_early_stop_confidence: 0.95
      planchet_stop_confidence: 0.90
      mousqueton_queue_confidence: 0.90

    model_selection:
      default:
        grimaud: haiku
        bazin: haiku
        planchet: haiku
        mousqueton: sonnet

      adaptive:
        enabled: true
        escalation_threshold: 0.80
        escalation_map:
          haiku: sonnet
          sonnet: opus
```

### 2.3 Métriques

**Fichier** : `src/monitoring/metrics.py`

**Tâches** :
- [ ] Ajouter compteurs pour chaque valet
- [ ] Ajouter histogramme de confiance par pass
- [ ] Ajouter taux d'arrêt précoce
- [ ] Ajouter coût par événement

**Métriques suggérées** :
```python
# Compteurs
four_valets_pass_total = Counter(
    "four_valets_pass_total",
    "Total passes executed",
    ["valet"]  # grimaud, bazin, planchet, mousqueton
)

four_valets_early_stop_total = Counter(
    "four_valets_early_stop_total",
    "Early stops by reason",
    ["valet", "reason"]
)

# Histogrammes
four_valets_confidence = Histogram(
    "four_valets_confidence",
    "Confidence by valet",
    ["valet"],
    buckets=[0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99]
)

# Gauges
four_valets_cost_per_event = Gauge(
    "four_valets_cost_per_event",
    "Average cost per event in USD"
)
```

---

## Phase 3 : Tests

### 3.1 Tests unitaires

**Fichier** : `tests/sancho/test_four_valets_analyzer.py`

**Tâches** :
- [ ] Test Grimaud early stop (spam, OTP)
- [ ] Test Bazin enrichissement
- [ ] Test Planchet stop à 90%+
- [ ] Test Mousqueton arbitrage
- [ ] Test flux complet (4 passes)
- [ ] Test sélection de modèle adaptative

**Cas de test prioritaires** :
```python
class TestFourValetsAnalyzer:
    async def test_grimaud_early_stop_on_spam(self):
        """Grimaud should stop early on obvious spam."""
        event = create_spam_event()
        result = await analyzer.analyze(event, empty_context)

        assert result.stopped_at == "grimaud"
        assert result.action == "delete"
        assert result.early_stop_reason == "spam"

    async def test_planchet_stops_at_high_confidence(self):
        """Planchet should stop if confidence > 90%."""
        event = create_simple_event()
        result = await analyzer.analyze(event, rich_context)

        assert result.stopped_at == "planchet"
        assert result.confidence.overall > 0.90

    async def test_mousqueton_called_on_low_confidence(self):
        """Mousqueton should be called if Planchet confidence <= 90%."""
        event = create_ambiguous_event()
        result = await analyzer.analyze(event, conflicting_context)

        assert result.stopped_at == "mousqueton"
        assert len(result.passes) == 4
```

### 3.2 Tests d'intégration

**Fichier** : `tests/integration/test_four_valets_integration.py`

**Tâches** :
- [ ] Test avec vrais appels API (mocked)
- [ ] Test de performance (latence)
- [ ] Test de coût (estimation)
- [ ] Test de rollback vers v2.2

### 3.3 Tests de comparaison

**Fichier** : `tests/comparison/test_v22_vs_v30.py`

**Tâches** :
- [ ] Comparer résultats v2.2 vs v3.0 sur dataset de référence
- [ ] Mesurer différence de confiance
- [ ] Mesurer différence de coût
- [ ] Identifier cas de régression

---

## Phase 4 : Déploiement

### 4.1 Shadow Mode

**Durée** : 1 semaine

**Tâches** :
- [ ] Activer v3.0 en parallèle de v2.2
- [ ] Logger résultats des deux versions
- [ ] Comparer sans impacter production
- [ ] Générer rapport de comparaison

### 4.2 A/B Testing

**Durée** : 2 semaines

**Tâches** :
- [ ] Router 10% du trafic vers v3.0
- [ ] Monitorer métriques clés
- [ ] Collecter feedback utilisateur
- [ ] Ajuster seuils si nécessaire

### 4.3 Rollout progressif

**Durée** : 2 semaines

**Tâches** :
- [ ] 10% → 25% → 50% → 100%
- [ ] Monitoring continu
- [ ] Rollback automatique si erreurs > seuil

### 4.4 Décommissionnement v2.2

**Durée** : 30 jours après 100%

**Tâches** :
- [ ] Conserver anciens templates en backup
- [ ] Supprimer code legacy après période de grâce
- [ ] Archiver métriques de comparaison

---

## Phase 5 : Documentation

### 5.1 Documentation technique

**Tâches** :
- [ ] Mettre à jour ARCHITECTURE.md
- [ ] Mettre à jour MULTI_PASS_SPEC.md (référencer v3.0)
- [ ] Documenter API de FourValetsAnalyzer

### 5.2 Documentation utilisateur

**Tâches** :
- [ ] Expliquer les 4 valets dans le user guide
- [ ] Documenter les métriques disponibles
- [ ] Ajouter FAQ sur les arrêts précoces

---

## Calendrier suggéré

| Phase | Tâches | Durée estimée |
|-------|--------|---------------|
| **Phase 1** | Préparation | 2-3 jours |
| **Phase 2** | Intégration | 2-3 jours |
| **Phase 3** | Tests | 3-4 jours |
| **Phase 4** | Déploiement | 5 semaines |
| **Phase 5** | Documentation | 1-2 jours |

**Total** : ~6-7 semaines pour déploiement complet

---

## Risques et mitigations

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Régression qualité | Haut | Shadow mode + A/B testing |
| Augmentation coût | Moyen | Seuils d'arrêt bien calibrés |
| Latence accrue | Moyen | Monitoring + alertes |
| Complexité debug | Faible | Logging détaillé par valet |

---

## Checklist de lancement

- [ ] Tous les tests passent
- [ ] Shadow mode validé (1 semaine)
- [ ] A/B testing validé (2 semaines)
- [ ] Métriques en place
- [ ] Alertes configurées
- [ ] Rollback testé
- [ ] Documentation à jour
- [ ] Équipe formée

---

## Contacts

- **Technique** : Johan
- **Review** : Claude (Architecture)
