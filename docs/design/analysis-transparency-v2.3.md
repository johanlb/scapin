# Analysis Transparency v2.3 - Design Document

**Version** : v1.0
**Date** : 18 janvier 2026
**Auteur** : Claude Code
**Statut** : Validé

---

## 1. Contexte et Motivation

### 1.1 Problème actuel

Le système Multi-Pass v2.2 capture des métadonnées riches sur l'analyse, mais l'utilisateur n'y a pas accès :

| Donnée capturée | Exposée à l'API | Affichée UI |
|-----------------|-----------------|-------------|
| `passes_count` | Non | Non |
| `final_model` | Non | Non |
| `escalated` | Non | Non |
| `stop_reason` | Non | Non |
| `pass_history` | Non | Non |
| `total_tokens` | Non | Non |
| `total_duration_ms` | Non | Non |
| `retrieved_context` | Oui | Oui (si non-null) |
| `context_influence` | Oui | Oui (si non-null) |

**Conséquence** : L'utilisateur ne comprend pas pourquoi certains emails ont du contexte et d'autres non.

### 1.2 Cas d'usage cibles

1. **Comprendre une décision** : "Pourquoi Scapin a classé cet email comme urgent ?"
2. **Debugger une mauvaise analyse** : "Quel modèle a été utilisé ? Le contexte a-t-il été consulté ?"
3. **Suivre une réanalyse** : "Où en est l'analyse ? Que se passe-t-il ?"
4. **Apprendre le système** : "Comment Scapin fonctionne-t-il ?"

---

## 2. Propositions

### 2.1 Niveau 1 : Métadonnées d'analyse (Quick Win)

**Objectif** : Exposer les métadonnées existantes dans l'API et les afficher.

#### 2.1.1 Nouveau modèle API

```python
class MultiPassMetadata(BaseModel):
    """Metadata from multi-pass analysis"""

    passes_count: int = Field(..., description="Number of passes executed")
    final_model: str = Field(..., description="Model used in final pass")
    escalated: bool = Field(False, description="Whether escalation occurred")
    stop_reason: str = Field("", description="Why analysis stopped")
    high_stakes: bool = Field(False, description="High-stakes email flag")
    total_tokens: int = Field(0, description="Total tokens consumed")
    total_duration_ms: float = Field(0, description="Total analysis time in ms")
    confidence_details: ConfidenceDetails | None = Field(None)


class PassHistoryEntry(BaseModel):
    """Single pass in analysis history"""

    pass_number: int
    pass_type: str  # blind_extraction, contextual_refinement, convergence, deep_reasoning
    model: str
    duration_ms: float
    tokens: int
    confidence_before: float
    confidence_after: float
    escalation_triggered: bool = False
    context_searched: bool = False
    notes_found: int = 0
```

#### 2.1.2 UI - Section "Analyse"

```
┌─────────────────────────────────────────────────────────────┐
│ 🔬 Analyse                                                  │
│                                                             │
│  ○───○───●      3 passes  •  Haiku → Sonnet                │
│                                                             │
│  ⏱ 2.3s   💬 1,247 tokens   📈 Escalade: oui               │
│  🛑 Arrêt: confidence_sufficient                            │
│                                                             │
│  [▼ Voir l'historique des passes]                          │
└─────────────────────────────────────────────────────────────┘
```

**Effort estimé** : 2-3h (API + UI)

---

### 2.2 Niveau 2 : Timeline des passes (Détail)

**Objectif** : Permettre de comprendre le cheminement de l'analyse.

#### 2.2.1 UI - Historique collapsible

```
┌─────────────────────────────────────────────────────────────┐
│ 📊 Historique des passes                               [▲]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─ Pass 1 ─────────────────────────────────────────────┐  │
│  │ 🟡 Haiku  •  blind_extraction  •  0.8s  •  312 tok   │  │
│  │                                                       │  │
│  │ Extraction aveugle sans contexte                      │  │
│  │ Confidence: 45% → 67%                                 │  │
│  │ 📈 Escalade décidée (< 85% et high_stakes)           │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌─ Pass 2 ─────────────────────────────────────────────┐  │
│  │ 🟠 Sonnet  •  contextual_refinement  •  1.2s         │  │
│  │                                                       │  │
│  │ 🔍 Recherche contexte:                               │  │
│  │    Entités: "Johan Labeeuw", "Acme Corp"             │  │
│  │    Notes trouvées: 3                                  │  │
│  │    Calendrier: 1 événement                            │  │
│  │                                                       │  │
│  │ Confidence: 67% → 85%                                 │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌─ Pass 3 ─────────────────────────────────────────────┐  │
│  │ 🟠 Sonnet  •  convergence  •  0.3s  •  346 tok       │  │
│  │                                                       │  │
│  │ Validation et convergence                             │  │
│  │ Confidence: 85% → 92%                                 │  │
│  │ ✅ Arrêt: confidence_sufficient                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2.2 Couleurs par modèle

| Modèle | Couleur | Signification |
|--------|---------|---------------|
| Haiku | 🟡 Jaune | Rapide, économique |
| Sonnet | 🟠 Orange | Équilibré |
| Opus | 🔴 Rouge | Puissant, coûteux |

**Effort estimé** : 3-4h

---

### 2.3 Niveau 3 : Temps réel pendant réanalyse (WebSocket)

**Objectif** : Feedback immédiat pendant l'analyse.

#### 2.3.1 Nouveaux événements WebSocket

```typescript
// Événements granulaires pour le suivi temps réel
interface AnalysisStartedEvent {
  type: 'analysis_started';
  item_id: string;
  email_subject: string;
  estimated_passes: number;  // 1-5 based on complexity hints
}

interface PassStartedEvent {
  type: 'pass_started';
  item_id: string;
  pass_number: number;
  pass_type: 'blind_extraction' | 'contextual_refinement' | 'convergence' | 'deep_reasoning' | 'coherence_validation';
  model: 'haiku' | 'sonnet' | 'opus';
}

interface ContextSearchingEvent {
  type: 'context_searching';
  item_id: string;
  entities_searching: string[];
  sources: string[];  // ['notes', 'calendar', 'tasks']
}

interface ContextFoundEvent {
  type: 'context_found';
  item_id: string;
  notes_count: number;
  calendar_count: number;
  tasks_count: number;
  entity_profiles_count: number;
}

interface PassCompletedEvent {
  type: 'pass_completed';
  item_id: string;
  pass_number: number;
  confidence: number;
  decision: 'continue' | 'escalate' | 'stop';
  reason?: string;
}

interface AnalysisCompletedEvent {
  type: 'analysis_completed';
  item_id: string;
  total_passes: number;
  final_confidence: number;
  action: string;
}

interface AnalysisErrorEvent {
  type: 'analysis_error';
  item_id: string;
  error: string;
  recoverable: boolean;
}
```

#### 2.3.2 UI - Composant AnalysisProgress

```svelte
<!-- Pendant la réanalyse -->
<div class="analysis-progress">
  <!-- Stepper visuel -->
  <div class="stepper">
    {#each passes as pass, i}
      <div class="step" class:active={i === currentPass} class:completed={i < currentPass}>
        <div class="step-circle">
          {#if i < currentPass}
            ✓
          {:else if i === currentPass}
            <Spinner size="sm" />
          {:else}
            {i + 1}
          {/if}
        </div>
        <div class="step-label">{pass.type}</div>
        <div class="step-model">{pass.model}</div>
      </div>
      {#if i < passes.length - 1}
        <div class="step-connector" class:active={i < currentPass}></div>
      {/if}
    {/each}
  </div>

  <!-- Message en cours -->
  <div class="current-action">
    {#if currentAction === 'searching_context'}
      <SearchingAnimation />
      <span>Recherche de contexte pour "{currentEntity}"...</span>
    {:else if currentAction === 'analyzing'}
      <ThinkingAnimation />
      <span>Analyse en cours avec {currentModel}...</span>
    {:else if currentAction === 'validating'}
      <CheckAnimation />
      <span>Validation de la cohérence...</span>
    {/if}
  </div>

  <!-- Log temps réel -->
  <div class="live-log">
    {#each logEntries as entry}
      <div class="log-entry" class:success={entry.type === 'success'}>
        <span class="timestamp">{entry.time}</span>
        <span class="message">{entry.message}</span>
      </div>
    {/each}
  </div>
</div>
```

#### 2.3.3 États visuels

| État | Visuel | Son (optionnel) |
|------|--------|-----------------|
| Démarrage | Pulse bleu | - |
| Pass en cours | Spinner + couleur modèle | - |
| Contexte trouvé | Flash vert | Subtle ding |
| Escalade | Transition couleur | - |
| Terminé | Check vert | Success chime |
| Erreur | Badge rouge | - |

**Effort estimé** : 6-8h (Backend + WebSocket + UI)

---

### 2.4 Niveau 4 : Badge de complexité (Liste Flux)

**Objectif** : Vue d'ensemble rapide de la "profondeur" d'analyse.

#### 2.4.1 Badges proposés

| Badge | Condition | Tooltip |
|-------|-----------|---------|
| `⚡` | 1 pass, Haiku | "Analyse rapide (1 pass)" |
| `⚡⚡` | 2 passes, no escalation | "Analyse standard (2 passes)" |
| `🔍` | Context searched | "Contexte utilisé" |
| `🧠` | 3+ passes | "Analyse approfondie" |
| `🏆` | Opus used | "Modèle premium utilisé" |
| `⚠️` | High stakes | "Email à enjeux" |

#### 2.4.2 Affichage compact

```
┌─────────────────────────────────────────────────────────────┐
│ 📧 Facture Acme Corp                          ⚡ 🔍        │
│    Il y a 2h • johan@example.com                            │
├─────────────────────────────────────────────────────────────┤
│ 📧 Proposition partenariat stratégique        🧠 🏆 ⚠️     │
│    Il y a 5h • ceo@bigcorp.com                              │
└─────────────────────────────────────────────────────────────┘
```

**Effort estimé** : 1-2h

---

## 3. Architecture technique

### 3.1 Flux de données actuel

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ MultiPass   │────▶│ QueueService│────▶│ API Response│
│ Analyzer    │     │ (conversion)│     │ (truncated) │
└─────────────┘     └─────────────┘     └─────────────┘
      │                                        │
      │ multi_pass: {                          │ ❌ multi_pass
      │   passes_count,                        │    non inclus
      │   final_model,                         │
      │   pass_history...                      │
      │ }                                      │
      ▼                                        ▼
  Stocké en DB                            Perdu pour UI
```

### 3.2 Flux de données proposé

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ MultiPass   │────▶│ QueueService│────▶│ API Response│
│ Analyzer    │     │ (enriched)  │     │ (complete)  │
└─────────────┘     └─────────────┘     └─────────────┘
      │                    │                   │
      │ Événements WS      │                   │ multi_pass: {
      ▼                    ▼                   │   ...
┌─────────────┐     ┌─────────────┐           │ }
│ WebSocket   │────▶│  Frontend   │           │ pass_history: [
│ Hub         │     │  (live)     │           │   ...
└─────────────┘     └─────────────┘           │ ]
                                              ▼
                                          UI complète
```

### 3.3 Points d'émission WebSocket

```python
# Dans multi_pass_analyzer.py

async def analyze(self, event: EmailEvent) -> MultiPassResult:
    # Émettre début d'analyse
    await self._emit_event(AnalysisStartedEvent(
        item_id=event.id,
        email_subject=event.subject,
        estimated_passes=self._estimate_complexity(event)
    ))

    for pass_num in range(1, self.max_passes + 1):
        pass_type = self._get_pass_type(pass_num)
        model = self._select_model(pass_num)

        # Émettre début de pass
        await self._emit_event(PassStartedEvent(
            item_id=event.id,
            pass_number=pass_num,
            pass_type=pass_type,
            model=model
        ))

        if pass_type == 'contextual_refinement':
            # Émettre recherche contexte
            await self._emit_event(ContextSearchingEvent(...))

            context = await self._search_context(...)

            # Émettre contexte trouvé
            await self._emit_event(ContextFoundEvent(...))

        result = await self._execute_pass(...)

        # Émettre fin de pass
        await self._emit_event(PassCompletedEvent(
            item_id=event.id,
            pass_number=pass_num,
            confidence=result.confidence,
            decision=self._decide_next(result)
        ))

        if self._should_stop(result):
            break

    # Émettre fin d'analyse
    await self._emit_event(AnalysisCompletedEvent(...))
```

---

## 4. Considérations UX

### 4.1 Progressive Disclosure

L'information doit être présentée en couches :

| Niveau | Visible par défaut | Contenu |
|--------|-------------------|---------|
| 1 | Oui | Badge complexité + résumé 1 ligne |
| 2 | Collapse fermé | Timeline des passes |
| 3 | Collapse fermé | Détails techniques (tokens, timing) |
| 4 | Mode debug | JSON brut |

### 4.2 Performance

- Les événements WebSocket doivent être **throttled** (max 1/100ms)
- L'historique des passes peut être **lazy loaded** au clic
- Le badge complexité doit être **calculé côté serveur** (pas de logique UI)

### 4.3 Accessibilité

- Les animations doivent respecter `prefers-reduced-motion`
- Les couleurs doivent avoir un contraste suffisant
- Le stepper doit être navigable au clavier

---

## 5. Métriques de succès

| Métrique | Baseline | Cible |
|----------|----------|-------|
| Temps pour comprendre une analyse | ? (non mesuré) | < 5s |
| Questions support "pourquoi cette décision" | ? | -50% |
| Satisfaction utilisateur (debug) | ? | > 4/5 |
| Latence perçue réanalyse | "long" | "acceptable" |

---

## 6. Phases d'implémentation

### Phase 1 : Fondations (v2.3.0)
- [ ] Exposer `multi_pass` dans l'API
- [ ] Afficher métadonnées de base dans UI
- [ ] Badge complexité dans liste Flux

### Phase 2 : Timeline (v2.3.1)
- [ ] Historique des passes collapsible
- [ ] Couleurs par modèle
- [ ] Détails par pass

### Phase 3 : Temps réel (v2.3.2)
- [ ] Nouveaux événements WebSocket
- [ ] Composant AnalysisProgress
- [ ] Intégration réanalyse

### Phase 4 : Polish (v2.3.3)
- [ ] Animations
- [ ] Sons (optionnel)
- [ ] Mode debug complet

---

## 7. Questions ouvertes

1. **Persistance** : Faut-il stocker l'historique complet des passes en DB ou seulement les métadonnées ?
2. **Rétrocompatibilité** : Comment gérer les analyses existantes sans `multi_pass` ?
3. **Mobile** : La timeline est-elle adaptée aux petits écrans ?
4. **Internationalisation** : Les `pass_type` doivent-ils être traduits ?

---

## 8. Idées avancées (Analyse approfondie)

Suite à une réflexion plus poussée, voici des idées complémentaires :

### 8.1 "Why not X?" - Explication des alternatives rejetées

**Problème** : L'utilisateur voit l'action recommandée mais pas pourquoi les autres ont été écartées.

**Solution** : Section "Alternatives considérées"

```
┌─────────────────────────────────────────────────────────────┐
│ 🤔 Pourquoi pas...                                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ❌ ARCHIVE (confiance: 34%)                                 │
│    "Contient une question directe nécessitant réponse"      │
│                                                             │
│ ❌ DELEGATE (confiance: 12%)                                │
│    "Aucun destinataire évident dans le contexte"            │
│                                                             │
│ ⚠️ REPLY (confiance: 78%) ← Recommandé                      │
│    "Question directe + deadline implicite"                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Implémentation** : Déjà capturé dans `options` mais pas affiché avec les raisons de rejet.

---

### 8.2 Graphique d'évolution de la confiance

**Problème** : Difficile de visualiser comment la confiance évolue entre les passes.

**Solution** : Mini-graphique sparkline

```
┌─────────────────────────────────────────────────────────────┐
│ 📈 Évolution de la confiance                                │
│                                                             │
│ 100% ┤                                    ●────────────     │
│  90% ┤                              ●─────┘                 │
│  80% ┤                        ●─────┘                       │
│  70% ┤                  ●─────┘                             │
│  60% ┤            ●─────┘                                   │
│  50% ┤      ●─────┘                                         │
│  40% ┤●─────┘                                               │
│      └──────┬──────┬──────┬──────┬──────┬──────────────     │
│           Pass 1  Pass 2  Pass 3  Pass 4  Final             │
│           Haiku   Sonnet  Sonnet  Sonnet                    │
│                                                             │
│ Seuil d'arrêt: 90% ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─                   │
└─────────────────────────────────────────────────────────────┘
```

**Bibliothèque** : `unovis` (déjà utilisé) ou simple SVG inline.

---

### 8.3 Transparence des coûts

**Problème** : L'utilisateur ne sait pas combien coûte une analyse.

**Solution** : Afficher le coût estimé en tokens et en euros/dollars

```
┌─────────────────────────────────────────────────────────────┐
│ 💰 Coût de l'analyse                                        │
│                                                             │
│ Tokens: 1,247 (input: 892, output: 355)                     │
│ Coût estimé: ~0.003€                                        │
│                                                             │
│ 📊 Comparaison:                                             │
│ ├─ Cette analyse: ████░░░░░░ (moyenne)                      │
│ ├─ Moyenne globale: 1,100 tokens                            │
│ └─ Email le plus coûteux: 8,432 tokens                      │
└─────────────────────────────────────────────────────────────┘
```

**Note** : Utile pour comprendre quand Opus est utilisé (10x plus cher).

---

### 8.4 Mode "Replay" - Debugger d'analyse

**Problème** : Pour les cas complexes, l'utilisateur veut comprendre étape par étape.

**Solution** : Interface de replay interactive

```
┌─────────────────────────────────────────────────────────────┐
│ 🔬 Mode Replay                              [◀ ▶] Step 3/7  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─ État actuel ─────────────────────────────────────────┐  │
│ │ Pass: 2 (contextual_refinement)                       │  │
│ │ Modèle: Sonnet                                         │  │
│ │ Confiance: 67%                                         │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
│ ┌─ Prompt envoyé ───────────────────────────────────────┐  │
│ │ Tu es un assistant... [Voir complet]                  │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
│ ┌─ Contexte injecté ────────────────────────────────────┐  │
│ │ • Note: "Johan Labeeuw" (relevance: 0.89)             │  │
│ │ • Calendrier: "RDV Acme" (demain 14h)                 │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
│ ┌─ Réponse IA ──────────────────────────────────────────┐  │
│ │ { "action": "REPLY", "confidence": 0.85, ... }        │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
│ [◀ Précédent]                              [Suivant ▶]     │
└─────────────────────────────────────────────────────────────┘
```

**Cas d'usage** : Debug avancé, formation, audit.

---

### 8.5 Score de contribution du contexte

**Problème** : On sait quel contexte a été trouvé, mais pas son impact réel.

**Solution** : Score de contribution par élément

```
┌─────────────────────────────────────────────────────────────┐
│ 🎯 Impact du contexte sur la décision                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Note "Johan Labeeuw"                                        │
│ ████████████████████░░░░░ 78% d'influence                  │
│ "A confirmé la relation professionnelle avec l'expéditeur"  │
│                                                             │
│ Calendrier "RDV Acme Corp"                                  │
│ ██████████░░░░░░░░░░░░░░░ 42% d'influence                  │
│ "A justifié l'urgence de la réponse"                        │
│                                                             │
│ Note "Projet Alpha"                                         │
│ ███░░░░░░░░░░░░░░░░░░░░░░ 12% d'influence                  │
│ "Contexte mineur, non déterminant"                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Implémentation** : Demander à l'IA d'évaluer l'influence de chaque élément.

---

### 8.6 Comparaison A/B d'analyses

**Problème** : Après une réanalyse, difficile de voir ce qui a changé.

**Solution** : Vue diff côte à côte

```
┌──────────────────────────┬──────────────────────────────────┐
│ Analyse originale        │ Réanalyse (Opus)                 │
├──────────────────────────┼──────────────────────────────────┤
│ Action: ARCHIVE          │ Action: REPLY ← Changé           │
│ Confiance: 72%           │ Confiance: 94% ↑                 │
│ Passes: 2                │ Passes: 4 ↑                      │
│ Modèle: Haiku            │ Modèle: Opus ↑                   │
│                          │                                  │
│ Contexte: aucun          │ Contexte: 3 notes ← Nouveau      │
│                          │                                  │
│ Reasoning:               │ Reasoning:                       │
│ "Email promotionnel      │ "Email de Johan Labeeuw,         │
│ sans action requise"     │ contact professionnel important, │
│                          │ question nécessitant réponse"    │
└──────────────────────────┴──────────────────────────────────┘
```

---

### 8.7 Prédiction de précision

**Problème** : L'utilisateur ne sait pas si Scapin a tendance à se tromper sur ce type d'email.

**Solution** : Indicateur basé sur l'historique

```
┌─────────────────────────────────────────────────────────────┐
│ 🎯 Fiabilité estimée                                        │
│                                                             │
│ Pour ce type d'email (facture, expéditeur connu):           │
│ ████████████████████░░░░░ 85% de précision historique       │
│                                                             │
│ Basé sur 23 emails similaires traités                       │
│ • 20 décisions confirmées par l'utilisateur                 │
│ • 3 corrections manuelles                                   │
│                                                             │
│ ⚠️ Attention: Confiance plus basse que d'habitude (72%)    │
└─────────────────────────────────────────────────────────────┘
```

**Implémentation** : Utiliser Sganarelle (apprentissage) pour calculer.

---

### 8.8 Export et audit trail

**Problème** : Pour des raisons de compliance ou debug, besoin d'exporter l'analyse.

**Solution** : Bouton d'export

```
┌─────────────────────────────────────────────────────────────┐
│ 📥 Exporter l'analyse                                       │
│                                                             │
│ ○ JSON complet (technique)                                  │
│ ○ PDF rapport (lisible)                                     │
│ ○ Markdown (documentation)                                  │
│                                                             │
│ Inclure:                                                    │
│ ☑ Métadonnées de l'email                                   │
│ ☑ Historique des passes                                    │
│ ☑ Contexte utilisé                                         │
│ ☐ Prompts complets (sensible)                              │
│ ☐ Réponses IA brutes (sensible)                            │
│                                                             │
│ [Exporter]                                                  │
└─────────────────────────────────────────────────────────────┘
```

---

### 8.9 Suggestions d'amélioration

**Problème** : L'utilisateur ne sait pas comment améliorer les analyses futures.

**Solution** : Recommandations contextuelles

```
┌─────────────────────────────────────────────────────────────┐
│ 💡 Pour améliorer les analyses futures                      │
│                                                             │
│ Cette analyse aurait pu être meilleure si:                  │
│                                                             │
│ • Une note "Acme Corp" existait avec les contacts clés      │
│   [+ Créer cette note]                                      │
│                                                             │
│ • Le calendrier contenait plus de contexte sur ce projet    │
│   [Voir événement]                                          │
│                                                             │
│ • L'expéditeur était dans votre carnet d'adresses           │
│   [+ Ajouter contact]                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 8.10 Mode "Explain Like I'm 5" (ELI5)

**Problème** : Les détails techniques ne sont pas accessibles à tous.

**Solution** : Explication simplifiée en langage naturel

```
┌─────────────────────────────────────────────────────────────┐
│ 🧒 En résumé simple                                         │
│                                                             │
│ "J'ai lu cet email 3 fois pour bien le comprendre.          │
│  La première fois, je n'étais pas sûr (67%).                │
│  Alors j'ai cherché dans tes notes et ton calendrier.       │
│  J'ai trouvé que tu connais cette personne (Johan).         │
│  Et tu as un rendez-vous avec son entreprise demain.        │
│  Du coup, je pense qu'il faut répondre vite (92% sûr)."     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Implémentation** : Générer via un prompt supplémentaire ou template.

---

### 8.11 "Thinking Bubbles" - Dialogue explicite entre passes (v2.3.1)

**Problème** : L'utilisateur voit le résultat mais pas le processus de réflexion de l'IA.

**Solution existante (backend)** : Le champ `next_pass_questions` dans `PassResult` permet aux passes de communiquer leurs doutes :

```
Pass 1 (Haiku, blind)
  │
  │ next_pass_questions: [
  │   "Qui est 'Marie' mentionnée ?",
  │   "Le 'Projet Alpha' existe-t-il dans les notes ?"
  │ ]
  ▼
Pass 2 (Sonnet, avec contexte)
  │ → Recherche contexte pour répondre aux questions
  │ → Affiche les questions comme "Points d'attention spéciaux"
  │
  │ next_pass_questions: [
  │   "Conflit détecté : Marie = Marie Dupont ou Marie Martin ?"
  │ ]
  ▼
Pass 4 (Expert)
  → Agrège toutes les questions non résolues
  → Répond explicitement avant décision finale
```

**Ce qui existe déjà** :
- `PassResult.next_pass_questions: list[str]` dans `convergence.py`
- Parsing dans `MultiPassAnalyzer._parse_response`
- Templates configurés (`pass1`, `pass2`, `pass4`)
- Tests de vérification (`tests/verify_cooperation.py`)

**Ce qui manque** :
- Exposition API (`PassHistoryEntryResponse.questions`)
- UI "Thinking Bubbles"

**UI proposée** :

```
┌─────────────────────────────────────────────────────────────┐
│ Dans la liste Flux (compact)                                │
│                                                             │
│ 📧 Email complexe                        💭 ⚡ 🔍           │
│    └─ 💭 = L'IA a eu des doutes (hover pour voir)          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Dans la timeline (détail)                                   │
│                                                             │
│  ┌─ Pass 1 ─────────────────────────────────────────────┐  │
│  │ 🟡 Haiku  •  blind  •  0.8s                          │  │
│  │ Confidence: 45% → 67%                                 │  │
│  │                                                       │  │
│  │ 💭 Questions pour la suite:                          │  │
│  │    • "Qui est 'Marie' ?"                             │  │
│  │    • "Projet Alpha existe-t-il ?"                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌─ Pass 2 ─────────────────────────────────────────────┐  │
│  │ 🟠 Sonnet  •  refine  •  1.2s                        │  │
│  │                                                       │  │
│  │ ✅ Réponses trouvées:                                │  │
│  │    • Marie = Marie Dupont (note trouvée)             │  │
│  │    • Projet Alpha = existe (créé le 12/01)           │  │
│  │                                                       │  │
│  │ 💭 Nouveau doute:                                    │  │
│  │    • "Deadline implicite ou explicite ?"             │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Implémentation API** :

```python
class PassHistoryEntryResponse(BaseModel):
    # ... champs existants ...
    questions: list[str] = Field(
        default_factory=list,
        description="Questions/doutes pour la passe suivante"
    )
```

**Implémentation UI** :
- Badge 💭 dans la liste si `pass_history.some(p => p.questions.length > 0)`
- Tooltip/popover au hover montrant les questions
- Dans la timeline : section collapsible par pass

**Philosophie UX** : "Show Your Work" - Montrer les doutes de l'IA renforce la confiance plus qu'un silence face à l'incertitude.

---

## 9. Décisions de design (Validées le 18/01/2026)

### 9.1 Badges

| Décision | Valeur |
|----------|--------|
| Cumul | **Oui** - Les badges se cumulent (ex: `🧠 🔍 🏆`) |
| `⚡` | 1 pass uniquement, modèle Haiku |
| `🔍` | `retrieved_context` non vide (contexte recherché) |
| `🧠` | 3 passes ou plus |
| `🏆` | Opus utilisé (dans n'importe quel pass) |

**Exemple d'affichage** :
```
📧 Email simple               ⚡
📧 Email avec contexte        ⚡ 🔍
📧 Analyse approfondie        🧠 🔍
📧 Analyse premium            🧠 🔍 🏆
```

### 9.2 Format métadonnées

| Élément | Format | Exemple |
|---------|--------|---------|
| Passes | Nombre entier | "3 passes" |
| Modèles | Tous les intermédiaires | "Haiku → Sonnet → Sonnet" |
| Durée | Secondes avec 1 décimale | "0.8s", "2.3s" |
| Séparateur | Bullet (•) | "3 passes • Haiku → Sonnet • 2.3s" |

### 9.3 Fallback anciennes analyses

Pour les analyses sans données `multi_pass` :
- Afficher : **"Analyse legacy"**
- Masquer la section timeline
- Les badges ne s'affichent pas

### 9.4 "Why not X?" - Backend enrichi

Le backend doit capturer les raisons de rejet pour chaque alternative :

```python
class ActionOption:
    action: str
    confidence: float
    reasoning: str           # Pourquoi cette option
    rejection_reason: str    # Pourquoi PAS cette option (si non recommandée)
```

### 9.5 Affichage confiance

- **Score global uniquement** (pas de décomposition 4D)
- Format : "67% → 85% → 92%"
- Dans la timeline : afficher avant/après par pass

### 9.6 Sparkline

- **SVG inline** (pas de librairie externe)
- Simple ligne avec points aux valeurs de confiance
- Couleur : dégradé du rouge (bas) au vert (haut)

### 9.7 "Thinking Bubbles" (next_pass_questions)

| Décision | Valeur |
|----------|--------|
| Champ API | `questions: list[str]` dans `PassHistoryEntryResponse` |
| Badge liste | 💭 si au moins une passe a des questions |
| Position badge | Avant les autres badges (💭 ⚡ 🔍 🧠 🏆) |
| Affichage détail | Dans la timeline, section par passe |
| Tooltip liste | "L'IA a eu des doutes pendant l'analyse" |

**Source backend** : `PassResult.next_pass_questions` (déjà implémenté)

---

## 10. Scope retenu

### P0 - Quick wins (v2.3.0)
| Idée | Description | Effort |
|------|-------------|--------|
| **Métadonnées de base** | "3 passes • Haiku → Sonnet • 2.3s" | ★★☆☆☆ |
| **Badge complexité** | `⚡` `🔍` `🧠` `🏆` dans la liste | ★☆☆☆☆ |

### P1 - Fort impact (v2.3.1)
| Idée | Description | Effort |
|------|-------------|--------|
| **Thinking Bubbles** | 💭 Afficher les doutes/questions de l'IA | ★★☆☆☆ |
| **Timeline des passes** | Historique collapsible avec détails | ★★★☆☆ |
| **Graphique confiance** | Sparkline de l'évolution 45% → 92% | ★★☆☆☆ |
| **"Why not X?"** | Explication des alternatives rejetées | ★★☆☆☆ |

### P2 - Différenciants (v2.3.2+)
| Idée | Description | Effort |
|------|-------------|--------|
| **Temps réel WebSocket** | Feedback live pendant réanalyse | ★★★★☆ |
| **Mode ELI5** | "J'ai lu cet email 3 fois..." | ★★☆☆☆ |
| **Score contribution** | % d'influence par note | ★★★☆☆ |
| **Coûts** | "~0.003€" | ★★☆☆☆ |
| **Suggestions** | "Une note Acme Corp améliorerait..." | ★★★☆☆ |

### Exclu du scope
- ~~Mode Replay~~ (trop complexe)
- ~~Export audit~~ (pas prioritaire)
- ~~Prédiction précision~~ (dépend de Sganarelle maturity)
- ~~Comparaison A/B~~ (peut-être plus tard)

---

## 10. Plan d'implémentation

### Phase 1 : v2.3.0 - Fondations
```
┌─────────────────────────────────────────────────────────────┐
│ Backend                                                     │
│ ├─ Ajouter MultiPassMetadata à QueueItemAnalysis           │
│ ├─ Ajouter PassHistoryEntry[] à QueueItemAnalysis          │
│ └─ Exposer dans queue_service.py                           │
├─────────────────────────────────────────────────────────────┤
│ Frontend                                                    │
│ ├─ Types TypeScript pour multi_pass                        │
│ ├─ Section "Analyse" dans flux/[id]                        │
│ └─ Badge complexité dans flux list                         │
└─────────────────────────────────────────────────────────────┘
```

#### Modèles API implémentés (src/jeeves/api/models/queue.py)

```python
class PassHistoryEntryResponse(BaseModel):
    """Single pass in multi-pass analysis history (v2.3)"""
    pass_number: int          # 1-5
    pass_type: str            # blind, refine, deep, expert
    model: str                # haiku, sonnet, opus
    duration_ms: float
    tokens: int
    confidence_before: float  # 0-1
    confidence_after: float   # 0-1
    context_searched: bool
    notes_found: int
    escalation_triggered: bool
    questions: list[str]      # v2.3.1: next_pass_questions (Thinking Bubbles)

class MultiPassMetadataResponse(BaseModel):
    """Metadata from multi-pass analysis (v2.3)"""
    passes_count: int         # 1-5
    final_model: str          # haiku, sonnet, opus
    models_used: list[str]    # ['haiku', 'sonnet', 'sonnet']
    escalated: bool
    stop_reason: str          # confidence_sufficient, max_passes, no_changes
    high_stakes: bool
    total_tokens: int
    total_duration_ms: float
    pass_history: list[PassHistoryEntryResponse]
```

#### Queue Service Implementation (src/jeeves/api/services/queue_service.py)

La méthode `_build_multi_pass_metadata()` construit les métadonnées à partir du `MultiPassResult`:

```python
def _build_multi_pass_metadata(self, result: Any) -> dict[str, Any]:
    """Build multi-pass metadata for API response."""
    models_used = []
    pass_history = []
    prev_confidence = 0.0

    for i, pass_result in enumerate(result.pass_history):
        model = pass_result.model_used
        models_used.append(model)

        # Detect context search (refine/deep passes)
        pass_type_value = pass_result.pass_type.value
        context_searched = pass_type_value in ["refine", "deep"]

        # Build per-pass entry
        pass_history.append({
            "pass_number": pass_result.pass_number,
            "pass_type": pass_type_value,
            "model": model,
            "duration_ms": pass_result.duration_ms,
            "tokens": pass_result.tokens_used,
            "confidence_before": prev_confidence,
            "confidence_after": pass_result.confidence.overall,
            "context_searched": context_searched,
            "notes_found": len(result.retrieved_context.get("notes", [])) if context_searched else 0,
            "escalation_triggered": was_escalation(models_used, i),
        })
        prev_confidence = pass_result.confidence.overall

    return {
        "passes_count": result.passes_count,
        "final_model": result.final_model,
        "models_used": models_used,
        "escalated": result.escalated,
        "stop_reason": result.stop_reason,
        "high_stakes": result.high_stakes,
        "total_tokens": result.total_tokens,
        "total_duration_ms": result.total_duration_ms,
        "pass_history": pass_history,
    }
```

#### TypeScript Types (web/src/lib/api/client.ts)

```typescript
export interface PassHistoryEntry {
  pass_number: number;
  pass_type: 'blind' | 'refine' | 'deep' | 'expert' | string;
  model: 'haiku' | 'sonnet' | 'opus' | string;
  duration_ms: number;
  tokens: number;
  confidence_before: number;  // 0-1
  confidence_after: number;   // 0-1
  context_searched: boolean;
  notes_found: number;
  escalation_triggered: boolean;
  questions: string[];        // v2.3.1: Thinking Bubbles (next_pass_questions)
}

export interface MultiPassMetadata {
  passes_count: number;
  final_model: 'haiku' | 'sonnet' | 'opus' | string;
  models_used: string[];
  escalated: boolean;
  stop_reason: 'confidence_sufficient' | 'max_passes' | 'no_changes' | string;
  high_stakes: boolean;
  total_tokens: number;
  total_duration_ms: number;
  pass_history: PassHistoryEntry[];
}
```

### Phase 2 : v2.3.1 - Visualisation
```
┌─────────────────────────────────────────────────────────────┐
│ Frontend                                                    │
│ ├─ Composant <PassTimeline>                                │
│ ├─ Composant <ConfidenceSparkline>                         │
│ └─ Section "Pourquoi pas X?" avec options rejetées         │
└─────────────────────────────────────────────────────────────┘
```

### Phase 3 : v2.3.2 - Temps réel
```
┌─────────────────────────────────────────────────────────────┐
│ Backend                                                     │
│ ├─ Nouveaux événements WebSocket (pass_started, etc.)      │
│ └─ Émission dans multi_pass_analyzer.py                    │
├─────────────────────────────────────────────────────────────┤
│ Frontend                                                    │
│ ├─ Composant <AnalysisProgress>                            │
│ ├─ Animations et feedback visuel                           │
│ └─ Intégration dans réanalyse                              │
└─────────────────────────────────────────────────────────────┘
```

### Phase 4 : v2.3.3 - Polish
```
┌─────────────────────────────────────────────────────────────┐
│ Backend                                                     │
│ ├─ Génération ELI5 (prompt ou template)                    │
│ ├─ Calcul score contribution contexte                      │
│ └─ Calcul coût en euros                                    │
├─────────────────────────────────────────────────────────────┤
│ Frontend                                                    │
│ ├─ Section "En résumé simple" (ELI5)                       │
│ ├─ Barres de contribution par note                         │
│ ├─ Affichage coût                                          │
│ └─ Suggestions d'amélioration                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Annexes

### A. Références

- [Context Transparency v2.2.2](../archive/session-history/2026-01-07-to-2026-01-17.md)
- [Multi-Pass Architecture](../../ARCHITECTURE.md#multi-pass-v22)
- [WebSocket Implementation](../../src/jeeves/api/routers/websocket.py)

### B. Mockups

(À ajouter après validation du concept)

---

## 11. Implementation Status

### Phase 1 : v2.3.0 - Fondations ✅ COMPLETED

**Commits**: `fc3cd70`, `f63c734` (18 janvier 2026)

| Composant | Fichier | Status |
|-----------|---------|--------|
| API Models | `src/jeeves/api/models/queue.py` | ✅ |
| Queue Service | `src/jeeves/api/services/queue_service.py` | ✅ |
| TypeScript Types | `web/src/lib/api/client.ts` | ✅ |
| Section Analyse UI | `web/src/routes/flux/[id]/+page.svelte` | ✅ |
| Badges Complexité | `web/src/routes/flux/+page.svelte` | ✅ |
| Légende Badges | `web/src/routes/flux/+page.svelte` | ✅ |
| Tests E2E | `web/e2e/pages/flux.spec.ts`, `flux-detail.spec.ts` | ✅ |
| Sélecteurs Test | `web/e2e/fixtures/test-data.ts` | ✅ |

**Fonctionnalités livrées** :
- Métadonnées multi-pass exposées via API (`multi_pass` dans `QueueItemAnalysis`)
- Section "🔬 Analyse" dans page détail flux avec:
  - Nombre de passes, modèles utilisés, durée
  - Badge escalade si applicable
  - Badge high-stakes si applicable
  - Raison d'arrêt traduite
  - Détails techniques collapsibles (tokens, historique)
- Badges de complexité dans la liste flux:
  - ⚡ Quick (1 pass Haiku)
  - 🔍 Context (contexte recherché)
  - 🧠 Complex (escalade)
  - 🏆 Opus (modèle expert utilisé)
- Légende des badges avec tooltips

---

### Phase 2 : v2.3.1 - Visualisation ✅ COMPLETED

**Commits**: `f46d033`, `8def936`, `0f6cb4b`, `22b9eb1` (19 janvier 2026)

| Composant | Fichier | Status |
|-----------|---------|--------|
| API: questions field | `src/jeeves/api/models/queue.py` | ✅ |
| API: rejection_reason | `src/jeeves/api/models/queue.py` | ✅ |
| Propagation questions | `src/jeeves/api/services/queue_service.py` | ✅ |
| PassTimeline Component | `web/src/lib/components/flux/PassTimeline.svelte` | ✅ |
| ConfidenceSparkline | `web/src/lib/components/flux/ConfidenceSparkline.svelte` | ✅ |
| Why Not Section | `web/src/routes/flux/[id]/+page.svelte` | ✅ |
| TypeScript Types | `web/src/lib/api/client.ts` | ✅ |
| Tests E2E | `web/e2e/pages/flux-detail.spec.ts` | ✅ |

**Fonctionnalités livrées** :

#### 2.1 API Fields (commit `f46d033`)
- `questions: list[str]` dans `PassHistoryEntryResponse` - Questions/doutes de l'IA entre passes (Thinking Bubbles)
- `rejection_reason: str | None` dans `ActionOptionResponse` - Explication de pourquoi une option n'est pas recommandée

#### 2.2 PassTimeline (commit `8def936`)
- Composant `<PassTimeline>` avec timeline visuelle
- Nœuds colorés par modèle (🟢 Haiku, 🟠 Sonnet, 🔴 Opus)
- Affichage par passe : type, durée, évolution confiance
- Badges : 🔍 contexte, ↑ escalade, 💭 questions
- Section "Thinking Bubbles" avec liste des questions/doutes
- Tooltips d'aide utilisateur sur tous les éléments

#### 2.3 ConfidenceSparkline (commit `0f6cb4b`)
- Composant SVG `<ConfidenceSparkline>` inline
- Graphique mini montrant l'évolution de la confiance
- Couleur adaptative (vert/orange/rouge selon résultat)
- Points sur chaque valeur avec tooltips
- Intégré dans la ligne de résumé multi-pass

#### 2.4 Why Not Section (commit `22b9eb1`)
- `rejection_reason` affiché inline sur les options non recommandées
- Section collapsible "🤔 Pourquoi pas les autres options?"
- Liste des alternatives rejetées avec leurs raisons
- Tooltips explicatifs

---

### Phase 2.5 : Bug Fix & UI Integration ✅ COMPLETED

**Commits**: `1b3d552`, `d916ead` (19 janvier 2026)

| Composant | Fichier | Status |
|-----------|---------|--------|
| API Conversion Functions | `src/jeeves/api/routers/queue.py` | ✅ |
| Debug Logging | `src/jeeves/api/services/queue_service.py` | ✅ |
| Transparency Section Main Page | `web/src/routes/flux/+page.svelte` | ✅ |

**Problème résolu** :
- Le champ `multi_pass` était toujours `null` dans les réponses API malgré une analyse réussie
- Les composants de transparence (PassTimeline, ConfidenceSparkline) n'étaient visibles que sur la page détail `/flux/[id]/+page.svelte`, pas sur la page principale `/flux/+page.svelte`

**Cause racine** :
- Les fonctions de conversion dans `queue.py` (`_convert_analysis_to_response()`) ne passaient pas les champs `multi_pass`, `retrieved_context`, et `context_influence` au modèle Pydantic

**Corrections apportées** :
1. Ajout de 3 fonctions de conversion dans `queue.py`:
   - `_convert_multi_pass_metadata()` : Convertit le dict raw → `MultiPassMetadataResponse`
   - `_convert_retrieved_context()` : Convertit le contexte récupéré
   - `_convert_context_influence()` : Convertit l'influence du contexte
2. Passage des champs de transparence à `QueueItemAnalysis` dans `_convert_analysis_to_response()`
3. Ajout de logging de debug dans `queue_service.py` pour tracer le flux de données
4. Ajout de la "Section 8.5: Analysis Transparency" sur la page principale flux avec tous les composants visuels

---

### Phase 3 : v2.3.2 - Temps Réel (PLANNED)

**Status**: Non démarré

| Fonctionnalité | Description | Priorité |
|----------------|-------------|----------|
| WebSocket events | `pass_started`, `pass_completed`, `analysis_done` | P1 |
| AnalysisProgress | Composant de progression en temps réel | P1 |
| Animations | Feedback visuel pendant analyse | P2 |

---

### Phase 4 : v2.3.3 - Polish (PLANNED)

**Status**: Non démarré

| Fonctionnalité | Description | Priorité |
|----------------|-------------|----------|
| Mode ELI5 | "J'ai lu cet email 3 fois..." | P2 |
| Score contribution | % d'influence par note | P2 |
| Affichage coût | "~0.003€" par analyse | P3 |
| Suggestions | "Une note Acme Corp améliorerait..." | P3 |

---

### Composants créés

```
web/src/lib/components/flux/
├── PassTimeline.svelte        # Timeline visuelle des passes (v2.3.1)
└── ConfidenceSparkline.svelte # Mini graphique confiance (v2.3.1)
```

### Sélecteurs E2E ajoutés

```typescript
// Pass Timeline (v2.3.1)
passTimeline: '[data-testid="pass-timeline"]'
timelinePass: (n) => `[data-testid="timeline-pass-${n}"]`
timelineContextBadge: '[data-testid="timeline-context-badge"]'
timelineEscalationBadge: '[data-testid="timeline-escalation-badge"]'
timelineThinkingBadge: '[data-testid="timeline-thinking-badge"]'
timelineQuestions: '[data-testid="timeline-questions"]'

// Confidence Sparkline (v2.3.1)
confidenceSparkline: '[data-testid="confidence-sparkline"]'

// Why Not Section (v2.3.1)
whyNotSection: '[data-testid="why-not-section"]'
whyNotItem: '[data-testid="why-not-item"]'
optionRejectionReason: '[data-testid="option-rejection-reason"]'
```
