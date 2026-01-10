# Bug #51 : Amélioration du système d'analyse IA

**Date** : 10 janvier 2026
**Priorité** : HAUTE
**Statut** : Investigation complète, améliorations proposées

---

## Problèmes identifiés par l'utilisateur

1. **Mauvaises actions** : L'IA propose Archive au lieu de Créer tâche, etc.
2. **Mauvais dossiers** : Action correcte mais classement incorrect
3. **Confiance trop haute** : L'IA est trop sûre d'elle sur des cas incertains
4. **Manque de contexte** : L'IA ne semble pas connaître les personnes/projets
5. **Pas d'apprentissage** : Les mêmes erreurs se répètent malgré les corrections

---

## Analyse des causes racines

### 1. Apprentissage non effectif

**Diagnostic** : Sganarelle existe mais n'influence pas les décisions futures.

| Composant | Statut | Problème |
|-----------|--------|----------|
| `FeedbackProcessor` | ✅ Implémenté | Calcule les scores mais... |
| `PatternStore` | ✅ Implémenté | Stocke les patterns mais... |
| `LearningEngine.learn()` | ⚠️ Appelé ? | Vérifier si invoqué après feedback |
| **Injection des patterns** | ❌ **MANQUANT** | Les patterns ne sont PAS injectés dans les prompts ! |

**Cause racine** : Les patterns appris ne sont pas utilisés lors de l'analyse suivante.
Le `PatternStore.find_matching_patterns()` existe mais n'est pas appelé dans `ReasoningEngine`.

### 2. Confiance artificiellement haute

**Diagnostic** : Le système accumule la confiance sans vrai feedback.

```python
# Problème dans reasoning_engine.py
Pass 1: 65% (estimation initiale)
Pass 2: 78% (+13% car contexte trouvé - même si non pertinent)
Pass 3: 88% (+10% car chain-of-thought terminé)
Pass 4: 91% (+3% stub bonus)
→ Toujours > 88% même sur des cas incertains !
```

**Cause racine** : Chaque pass ajoute de la confiance sans validation réelle.

### 3. Contexte insuffisant

**Diagnostic** : Le ContextEngine est connecté mais :
- Base de notes potentiellement vide/pauvre
- Embeddings non calculés pour nouvelles notes
- Seuil `min_relevance: 0.3` peut filtrer trop

### 4. Prompts trop génériques

**Diagnostic** : Les templates ne contiennent pas :
- Exemples de décisions passées de l'utilisateur
- Préférences de classement par dossier
- Règles métier spécifiques

---

## Améliorations proposées

### Phase 1 : Quick Wins (1-2 jours)

#### 1.1 Injecter les patterns appris dans les prompts

```python
# Dans ReasoningEngine._pass1_initial_analysis()
matching_patterns = self.pattern_store.find_matching_patterns(event)
if matching_patterns:
    # Ajouter au prompt :
    # "Basé sur les décisions précédentes de l'utilisateur :
    #  - Emails de [sender] → généralement [action] (85% succès)
    #  - Sujet contenant [keyword] → [action]"
```

**Fichiers à modifier** :
- `src/sancho/reasoning_engine.py` : Injecter patterns
- `templates/ai/pass1_initial.j2` : Ajouter section "Historique décisions"

#### 1.2 Réduire la confiance de base

```python
# Actuellement
CONFIDENCE_BOOST_CONTEXT = 0.13  # +13%
CONFIDENCE_BOOST_DEEP = 0.10     # +10%

# Proposé
CONFIDENCE_BOOST_CONTEXT = 0.05  # +5% seulement si contexte VRAIMENT pertinent
CONFIDENCE_BOOST_DEEP = 0.05     # +5% seulement si alternatives explorées
```

#### 1.3 Logger les feedbacks pour debug

```python
# Ajouter dans queue_router.py après approve/reject
logger.info("Feedback received", extra={
    "item_id": item_id,
    "action": "approve" | "reject",
    "original_action": item.proposed_action,
    "user_action": modified_action,
    "confidence_was": item.confidence,
    "learning_triggered": True | False
})
```

### Phase 2 : Améliorations moyennes (3-5 jours)

#### 2.1 Few-shot learning personnalisé

Stocker les 10 dernières décisions correctes et les injecter comme exemples :

```jinja2
{# templates/ai/pass1_initial.j2 #}
## Exemples de décisions passées (approuvées par l'utilisateur)

{% for example in recent_approved_decisions[:5] %}
Email: "{{ example.subject }}" de {{ example.sender }}
→ Action: {{ example.action }} dans {{ example.folder }}
{% endfor %}

## Email à analyser maintenant
...
```

#### 2.2 Calibration active de la confiance

Après chaque feedback, ajuster immédiatement :

```python
# Si user rejette une décision à 90% confiance
# → Réduire le score de confiance des décisions similaires futures

calibrator.immediate_adjust(
    predicted_confidence=0.90,
    actual_correctness=0.20,  # rejected
    event_signature=event.signature
)
```

#### 2.3 Règles de classement par dossier

Permettre à l'utilisateur de définir des règles :

```yaml
# config/folder_rules.yaml
rules:
  - condition: "sender contains 'newsletter'"
    action: archive
    folder: "Newsletters"

  - condition: "subject contains 'facture' OR 'invoice'"
    action: archive
    folder: "Finance/Factures"

  - condition: "sender domain = 'company.com'"
    action: review
    folder: "Work/Internal"
```

### Phase 3 : Améliorations majeures (1-2 semaines)

#### 3.1 Fine-tuning du modèle (optionnel)

Créer un dataset de décisions correctes et fine-tuner un modèle :
- Collecter 500+ décisions approuvées
- Format : (email, action_correcte, dossier_correct)
- Fine-tune Claude ou utiliser retrieval-augmented generation

#### 3.2 Multi-provider consensus (Phase 2.5)

Demander à 2+ modèles et voter :
```
Claude Sonnet: Archive → Finance (85%)
GPT-4: Archive → Finance (82%)
Mistral: Task → Work (45%)

Consensus: Archive → Finance (83.5%)
```

#### 3.3 UI de feedback enrichie

Permettre à l'utilisateur de :
- Corriger le dossier proposé (avec autocomplete)
- Expliquer pourquoi il rejette ("trop confiant", "mauvais contexte")
- Définir des règles on-the-fly ("toujours archiver les emails de X")

---

## Plan d'action recommandé

| Priorité | Action | Impact | Effort |
|----------|--------|--------|--------|
| 🔴 P0 | 1.1 Injecter patterns dans prompts | HAUT | 2h |
| 🔴 P0 | 1.3 Logger feedbacks pour debug | MOYEN | 1h |
| 🟠 P1 | 1.2 Réduire confiance de base | MOYEN | 1h |
| 🟠 P1 | 2.1 Few-shot personnalisé | HAUT | 4h |
| 🟡 P2 | 2.2 Calibration active | MOYEN | 4h |
| 🟡 P2 | 2.3 Règles de dossiers | HAUT | 6h |
| 🟢 P3 | 3.3 UI feedback enrichie | HAUT | 8h |

---

## Métriques de succès

| Métrique | Actuel | Objectif |
|----------|--------|----------|
| Taux d'approbation directe | ~30% ? | > 70% |
| Corrections de dossier | ~50% ? | < 20% |
| Confiance moyenne des erreurs | ~85% | < 60% |
| Amélioration après 50 feedbacks | 0% | > 20% |

---

## Fichiers clés à modifier

```
src/sancho/reasoning_engine.py      # Injection patterns
src/sancho/templates.py             # Chargement few-shot
src/sganarelle/learning_engine.py   # Vérifier appel
src/sganarelle/pattern_store.py     # Persistance patterns
src/jeeves/api/routers/queue.py     # Logger feedback
templates/ai/pass1_initial.j2       # Few-shot section
templates/ai/pass2_context.j2       # Patterns section
```

---

*Document créé le 10 janvier 2026*
