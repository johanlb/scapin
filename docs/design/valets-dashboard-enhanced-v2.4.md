# Valets Dashboard Enhanced — Design Document v2.4

**Date** : 19 janvier 2026
**Auteur** : Claude
**Statut** : En cours d'implémentation
**PR Branch** : `claude/new-dedicated-page-fX6bF`

---

## 1. Objectif

Enrichir la page Valets existante (`/valets`) avec 4 nouvelles fonctionnalités majeures pour offrir une visibilité complète sur l'architecture cognitive de Scapin :

1. **Page détail valet** — Analytics approfondis par agent
2. **Workflow visuel** — Diagramme interactif du pipeline de traitement
3. **Dashboard coûts** — Répartition et projection des coûts IA
4. **Alertes santé** — Monitoring temps réel avec notifications

---

## 2. Architecture Existante

### 2.1 Fichiers actuels

| Fichier | Rôle |
|---------|------|
| `web/src/routes/valets/+page.svelte` | Page dashboard principale |
| `web/src/lib/stores/valets.svelte.ts` | Store Svelte 5 réactif |
| `src/jeeves/api/routers/valets.py` | Endpoints REST API |
| `src/jeeves/api/services/valets_stats_service.py` | Agrégation des stats |

### 2.2 API existante

```
GET  /api/valets                    → ValetsDashboardResponse
GET  /api/valets/metrics?period=    → ValetsMetricsResponse
GET  /api/valets/{valet_name}       → ValetInfo
GET  /api/valets/{valet_name}/activities → list[ValetActivity]
```

### 2.3 Les 7 Valets

| Valet | Icône | Module | Responsabilité |
|-------|-------|--------|----------------|
| Trivelin | 👁️ | `src/trivelin/` | Perception & triage |
| Sancho | 🧠 | `src/sancho/` | Raisonnement IA multi-pass |
| Passepartout | 📚 | `src/passepartout/` | Base de connaissances |
| Planchet | 📋 | `src/planchet/` | Planification & risques |
| Figaro | ⚡ | `src/figaro/` | Exécution des actions |
| Sganarelle | 🎓 | `src/sganarelle/` | Apprentissage continu |
| Jeeves | 🎭 | `src/jeeves/` | Interface API |

---

## 3. Phase 1 : Page Détail Valet

### 3.1 Objectif

Créer une page dédiée `/valets/[name]` affichant les analytics approfondis d'un valet spécifique.

### 3.2 Route

```
/valets/[name]/+page.svelte
```

### 3.3 Contenu de la page

1. **Header** : Icône, nom, description, badge statut
2. **Métriques clés** : Tâches aujourd'hui, erreurs, temps moyen, tokens
3. **Timeline d'activités** : Liste scrollable avec filtres (succès/erreur/tous)
4. **Graphique de performance** : Courbe sur 7 jours (tâches, erreurs, latence)
5. **Répartition modèles** (Sancho uniquement) : Camembert Haiku/Sonnet/Opus

### 3.4 Nouveaux composants

```
web/src/lib/components/valets/
├── ActivityTimeline.svelte      # Timeline verticale des activités
├── PerformanceChart.svelte      # Graphique SVG performance 7j
└── ModelUsageBreakdown.svelte   # Camembert utilisation modèles
```

### 3.5 API étendue

```python
# Nouveau endpoint
GET /api/valets/{name}/details → ValetDetailsResponse

class ValetDetailsResponse(BaseModel):
    info: ValetInfo
    activities: list[ValetActivity]  # 100 dernières
    performance_7d: list[DailyMetrics]  # 7 jours de métriques
    model_usage: ModelUsageStats | None  # Sancho uniquement
```

### 3.6 Maquette

```
┌─────────────────────────────────────────────────────────┐
│  ← Retour    🧠 Sancho                         [Actif]  │
│              Raisonnement IA multi-passes               │
├─────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │  127    │ │   3     │ │  245ms  │ │  45.2K  │       │
│  │ Tâches  │ │ Erreurs │ │ Moy.    │ │ Tokens  │       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
├─────────────────────────────────────────────────────────┤
│  Performance (7 jours)              Modèles utilisés    │
│  ┌─────────────────────┐           ┌───────────────┐   │
│  │    ╱╲    ╱╲         │           │   ◐ Haiku 45% │   │
│  │   ╱  ╲  ╱  ╲        │           │   ◑ Sonnet 40%│   │
│  │  ╱    ╲╱    ╲       │           │   ● Opus 15%  │   │
│  └─────────────────────┘           └───────────────┘   │
├─────────────────────────────────────────────────────────┤
│  Activités récentes                    [Tous ▼] 🔄     │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ● 14:32  Analyse email #4521          245ms  ✓  │   │
│  │ ● 14:30  Analyse email #4520          312ms  ✓  │   │
│  │ ● 14:28  Analyse email #4519          189ms  ✓  │   │
│  │ ○ 14:25  Analyse email #4518         1204ms  ✗  │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Phase 2 : Workflow Visuel

### 4.1 Objectif

Afficher un diagramme interactif du pipeline de traitement montrant le flux des emails à travers les valets.

### 4.2 Composant

```
web/src/lib/components/valets/WorkflowDiagram.svelte
```

### 4.3 Fonctionnalités

1. **Nœuds SVG** : Un nœud par valet avec icône et compteur
2. **Connexions animées** : Flèches entre les valets avec animation de flux
3. **État temps réel** : Nombre d'items en cours à chaque étape
4. **Détection goulots** : Highlight rouge si file > seuil
5. **Interactivité** : Clic sur un nœud → navigation vers `/valets/[name]`

### 4.4 API

```python
# Nouveau endpoint
GET /api/valets/pipeline → PipelineStatusResponse

class PipelineStage(BaseModel):
    valet: ValetType
    items_processing: int
    items_queued: int
    avg_processing_time_ms: int
    is_bottleneck: bool

class PipelineStatusResponse(BaseModel):
    stages: list[PipelineStage]
    total_in_pipeline: int
    estimated_completion_minutes: float
```

### 4.5 Maquette

```
┌─────────────────────────────────────────────────────────┐
│  Pipeline de traitement                          🔄     │
│                                                         │
│    ┌───┐     ┌───┐     ┌───┐     ┌───┐     ┌───┐      │
│    │👁️│ ──▶ │🧠│ ──▶ │📚│ ──▶ │📋│ ──▶ │⚡│      │
│    │ 3 │     │ 5 │     │ 1 │     │ 2 │     │ 0 │      │
│    └───┘     └───┘     └───┘     └───┘     └───┘      │
│  Trivelin   Sancho  Passepartout Planchet  Figaro      │
│                 ⚠️                                      │
│            Goulot détecté                              │
│                                                         │
│  Total en cours : 11 items • Temps estimé : ~3 min     │
└─────────────────────────────────────────────────────────┘
```

---

## 5. Phase 3 : Dashboard Coûts

### 5.1 Objectif

Donner une visibilité complète sur les coûts d'utilisation de l'IA avec répartition par modèle et projections.

### 5.2 Composants

```
web/src/lib/components/valets/
├── CostBreakdown.svelte      # Barres empilées par valet/modèle
├── EfficiencyChart.svelte    # Scatter confiance vs coût
└── BudgetProjection.svelte   # Projection mensuelle
```

### 5.3 API étendue

```python
# Extension de ValetsMetricsResponse
class ModelCosts(BaseModel):
    haiku_tokens: int
    haiku_cost_usd: float
    sonnet_tokens: int
    sonnet_cost_usd: float
    opus_tokens: int
    opus_cost_usd: float
    total_cost_usd: float

class CostMetrics(BaseModel):
    period: str
    costs_by_valet: dict[str, ModelCosts]
    total_cost_usd: float
    projected_monthly_usd: float
    cost_per_email_avg_usd: float
    confidence_per_dollar: float  # Efficacité

# Nouveau endpoint
GET /api/valets/costs?period= → CostMetricsResponse
```

### 5.4 Tarification de référence (janvier 2026)

| Modèle | Input ($/1M tokens) | Output ($/1M tokens) |
|--------|---------------------|----------------------|
| Haiku 3.5 | $0.80 | $4.00 |
| Sonnet 3.5 | $3.00 | $15.00 |
| Opus 4 | $15.00 | $75.00 |

### 5.5 Maquette

```
┌─────────────────────────────────────────────────────────┐
│  Coûts & Efficacité                     [7j ▼]         │
├─────────────────────────────────────────────────────────┤
│  Répartition par modèle          │  Projection         │
│  ┌───────────────────────┐       │  ┌───────────────┐  │
│  │████████░░░░░░░░░░░░░░│ Haiku  │  │ Mois en cours │  │
│  │████████████░░░░░░░░░░│ Sonnet │  │    $12.45     │  │
│  │██░░░░░░░░░░░░░░░░░░░░│ Opus   │  │ Projection    │  │
│  └───────────────────────┘       │  │    $18.20     │  │
│  Total : $4.52                   │  └───────────────┘  │
├─────────────────────────────────────────────────────────┤
│  Efficacité                                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Coût/email moy. : $0.035                       │   │
│  │  Confiance/$     : 2.43 points/%                │   │
│  │  Économies escalade intelligente : ~40%         │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Phase 4 : Alertes Santé

### 6.1 Objectif

Système de monitoring avec alertes configurables pour détecter les problèmes proactivement.

### 6.2 Service backend

```python
# src/jeeves/api/services/alerts_service.py

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class AlertRule:
    """Règle de déclenchement d'alerte"""
    name: str
    condition: Callable[..., bool]
    severity: AlertSeverity
    message_template: str

# Règles par défaut
DEFAULT_RULES = [
    AlertRule(
        name="high_error_rate",
        condition=lambda stats: stats.error_rate > 0.1,
        severity=WARNING,
        message="{valet} a un taux d'erreur élevé ({rate:.1%})"
    ),
    AlertRule(
        name="queue_growing",
        condition=lambda pipeline: pipeline.growth_rate > 5,
        severity=WARNING,
        message="File d'attente en croissance (+{rate}/min)"
    ),
    AlertRule(
        name="valet_error",
        condition=lambda valet: valet.status == "error",
        severity=CRITICAL,
        message="{valet} est en erreur"
    ),
    AlertRule(
        name="learning_stale",
        condition=lambda sganarelle: sganarelle.last_cycle > 24h,
        severity=INFO,
        message="Pas de cycle d'apprentissage depuis 24h"
    ),
]
```

### 6.3 API

```python
# Nouveau endpoint
GET /api/valets/alerts → AlertsResponse

class Alert(BaseModel):
    id: str
    severity: AlertSeverity
    valet: ValetType | None
    message: str
    triggered_at: datetime
    acknowledged: bool = False

class AlertsResponse(BaseModel):
    alerts: list[Alert]
    total_critical: int
    total_warning: int
    total_info: int
```

### 6.4 Composant

```
web/src/lib/components/valets/AlertsBanner.svelte
```

### 6.5 Maquette

```
┌─────────────────────────────────────────────────────────┐
│  🔴 1 critique  🟡 2 avertissements              [×]    │
├─────────────────────────────────────────────────────────┤
│  🔴 CRITIQUE  Sancho est en erreur                      │
│     Il y a 2 min • Cliquez pour voir les détails        │
│  ─────────────────────────────────────────────────────  │
│  🟡 AVERTISSEMENT  Taux d'erreur élevé (12%)            │
│     Trivelin • Il y a 5 min                             │
│  ─────────────────────────────────────────────────────  │
│  🟡 AVERTISSEMENT  File d'attente en croissance         │
│     +8 emails/min • Il y a 1 min                        │
└─────────────────────────────────────────────────────────┘
```

---

## 7. Structure des fichiers

### 7.1 Nouveaux fichiers à créer

```
# Backend
src/jeeves/api/services/alerts_service.py          # Service alertes
src/jeeves/api/models/valets.py                    # Modèles étendus

# Frontend - Routes
web/src/routes/valets/[name]/+page.svelte          # Page détail

# Frontend - Composants
web/src/lib/components/valets/ActivityTimeline.svelte
web/src/lib/components/valets/PerformanceChart.svelte
web/src/lib/components/valets/ModelUsageBreakdown.svelte
web/src/lib/components/valets/WorkflowDiagram.svelte
web/src/lib/components/valets/CostBreakdown.svelte
web/src/lib/components/valets/EfficiencyChart.svelte
web/src/lib/components/valets/BudgetProjection.svelte
web/src/lib/components/valets/AlertsBanner.svelte
```

### 7.2 Fichiers à modifier

```
src/jeeves/api/routers/valets.py                   # Nouveaux endpoints
src/jeeves/api/services/valets_stats_service.py    # Stats étendues
web/src/lib/stores/valets.svelte.ts                # Nouveaux états
web/src/lib/api/client.ts                          # Types TypeScript
web/src/routes/valets/+page.svelte                 # Intégration workflow + alertes
```

---

## 8. Plan d'implémentation

| Phase | Tâche | Priorité |
|-------|-------|----------|
| 1.1 | Créer route `/valets/[name]` | Haute |
| 1.2 | Endpoint `/valets/{name}/details` | Haute |
| 1.3 | Composants Timeline, Chart, ModelUsage | Haute |
| 2.1 | Composant WorkflowDiagram | Moyenne |
| 2.2 | Endpoint `/valets/pipeline` | Moyenne |
| 2.3 | Intégration sur page principale | Moyenne |
| 3.1 | Extension API coûts | Moyenne |
| 3.2 | Composants CostBreakdown, Efficiency, Budget | Moyenne |
| 3.3 | Section coûts sur page | Moyenne |
| 4.1 | Service AlertsService | Haute |
| 4.2 | Endpoint `/valets/alerts` | Haute |
| 4.3 | Composant AlertsBanner | Haute |

---

## 9. Critères de validation

- [ ] Navigation `/valets` → `/valets/[name]` fonctionnelle
- [ ] Graphiques SVG responsives et accessibles
- [ ] Alertes affichées en temps réel
- [ ] Coûts calculés avec précision
- [ ] Tests E2E passants
- [ ] 0 erreur TypeScript (`npm run check`)
- [ ] 0 warning Ruff

---

## 10. Références

- [CLAUDE.md](../../CLAUDE.md) — Contexte projet
- [ARCHITECTURE.md](../../ARCHITECTURE.md) — Architecture cognitive
- [Analysis Transparency v2.3](analysis-transparency-v2.3.md) — Précédent design similaire
