# Architecture des Quatre Valets — Spécification v3.0

**Date** : 2026-01-20
**Auteur** : Johan / Claude
**Status** : Draft

---

## 1. Vue d'ensemble

L'architecture "Quatre Valets" remplace le système multi-pass v2.2 par une approche inspirée des valets des Trois Mousquetaires de Dumas. Chaque valet a une personnalité et un rôle distincts, créant un dialogue coopératif et contradictoire entre les passes d'analyse.

### 1.1 Les Quatre Valets

| Pass | Valet | Maître | Personnalité | Rôle |
|------|-------|--------|--------------|------|
| 1 | **Grimaud** | Athos | Silencieux, économe en mots | Extraction brute |
| 2 | **Bazin** | Aramis | Érudit, méticuleux | Enrichissement contextuel |
| 3 | **Planchet** | d'Artagnan | Curieux, pragmatique | Critique et validation |
| 4 | **Mousqueton** | Porthos | Généreux, décisif | Arbitrage final |

### 1.2 Principes fondamentaux

1. **Dialogue entre valets** : Chaque valet reçoit le travail des précédents et peut le modifier
2. **Arrêt précoce** : Le processus peut s'arrêter avant la fin si la confiance est suffisante
3. **Propriété du résultat** : Celui qui arrête la chaîne possède le résultat final
4. **Sensibilité à l'âge** : Chaque valet interprète l'âge de l'événement différemment

---

## 2. Flux de traitement

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ÉVÉNEMENT PERÇU                               │
│                    (email, notification, etc.)                       │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  GRIMAUD (Pass 1) — Extraction silencieuse                          │
│  ─────────────────────────────────────────                          │
│  • Modèle : Haiku                                                   │
│  • Entrée : Événement brut + Briefing                               │
│  • Sortie : Extractions + Action + Confiance                        │
│  • Confiance cible : 60-80% (95%+ si éphémère)                      │
│                                                                      │
│  ARRÊT SI : early_stop=true ET action=delete ET confiance>95%       │
│            (contenu éphémère : OTP, spam, notification)              │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                          early_stop ?
                         /            \
                       OUI            NON
                        │              │
                        ▼              ▼
                   ┌────────┐   ┌─────────────────────────────────────┐
                   │  FIN   │   │  BAZIN (Pass 2) — Enrichissement    │
                   │Grimaud │   │  ───────────────────────────────    │
                   └────────┘   │  • Modèle : Haiku (ou Sonnet)       │
                                │  • Entrée : Grimaud + Mémoires PKM  │
                                │  • Sortie : Extractions enrichies   │
                                │  • Confiance cible : 80-95%         │
                                │                                      │
                                │  PAS D'ARRÊT — toujours → Planchet  │
                                └─────────────────────────────────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PLANCHET (Pass 3) — Critique et validation                         │
│  ──────────────────────────────────────────                         │
│  • Modèle : Haiku (ou Sonnet si escalade)                           │
│  • Entrée : Grimaud + Bazin + Mémoires                              │
│  • Sortie : Critique + Extractions ajustées + Confiance             │
│  • Confiance cible : 85-95%                                         │
│                                                                      │
│  ARRÊT SI : confidence > 90%                                        │
│            (extractions de Planchet = résultat final)               │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                        confidence > 90% ?
                         /            \
                       OUI            NON
                        │              │
                        ▼              ▼
                   ┌────────┐   ┌─────────────────────────────────────┐
                   │  FIN   │   │  MOUSQUETON (Pass 4) — Arbitrage    │
                   │Planchet│   │  ────────────────────────────────   │
                   └────────┘   │  • Modèle : Sonnet (ou Opus)        │
                                │  • Entrée : Tous les rapports       │
                                │  • Sortie : Verdict final           │
                                │  • Confiance cible : 90-99%         │
                                │                                      │
                                │  TOUJOURS DERNIER                   │
                                └─────────────────────────────────────┘
                                                  │
                                                  ▼
                                             ┌────────┐
                                             │  FIN   │
                                             │Mousq.  │
                                             └────────┘
```

---

## 3. Spécification par valet

### 3.1 Grimaud (Pass 1)

**Fichier** : `templates/ai/v2/pass1_grimaud.j2`

**Mission** : Observer et extraire. Rien de plus.

**Entrées** :
- `event` : Événement perçu (email, notification)
- `briefing` : Contexte utilisateur (profil, projets, objectifs)
- `now` : Date/heure actuelle (pour calcul d'âge)
- `max_content_chars` : Limite de contenu (défaut: 8000)

**Sorties** :
```json
{
  "extractions": [...],
  "action": "archive|flag|queue|delete|rien",
  "early_stop": false,
  "early_stop_reason": null,
  "confidence": {
    "entity_confidence": 0.75,
    "action_confidence": 0.70,
    "extraction_confidence": 0.80,
    "completeness": 0.65
  },
  "entities_discovered": ["..."],
  "reasoning": "...",
  "next_pass_questions": ["..."]
}
```

**Règles clés** :
- RÈGLE 0 : CORBEILLE — Supprimer les contenus éphémères
- RÈGLE 1 : SILENCE SÉLECTIF — Quand ne rien extraire
- RÈGLE 2 : ÉCONOMIE — Une extraction condensée
- RÈGLE 3 : CIBLAGE — Projet > Actif > Contact stratégique

**Arrêt précoce** :
- Condition : `action="delete"` + `early_stop=true` + confiance > 95%
- Raisons valides : `ephemeral_content`, `spam`, `otp`, `notification`

### 3.2 Bazin (Pass 2)

**Fichier** : `templates/ai/v2/pass2_bazin.j2`

**Mission** : Confronter l'observation aux mémoires.

**Entrées** :
- `event` : Événement perçu
- `briefing` : Contexte utilisateur
- `previous_result` : Rapport de Grimaud
- `context` : Contexte structuré (notes PKM, calendrier, tâches)
- `max_context_notes` : Nombre max de notes (défaut: 5)

**Sorties** :
```json
{
  "extractions": [...],
  "action": "...",
  "confidence": {...},
  "entities_discovered": ["..."],
  "changes_made": ["..."],
  "context_influence": {
    "notes_used": ["..."],
    "explanation": "...",
    "confirmations": ["..."],
    "contradictions": ["..."],
    "missing_info": ["..."]
  },
  "reasoning": "...",
  "next_pass_questions": ["..."]
}
```

**Tâches** :
1. IDENTIFIER — Résoudre les ambiguïtés de noms
2. VÉRIFIER — Détecter les doublons
3. ENRICHIR — Ajouter le contexte manquant
4. AJUSTER — Adapter les actions (omnifocus, calendar)
5. ÉVALUER — Mettre à jour la confiance

**Pas d'arrêt** : Toujours passer à Planchet.

### 3.3 Planchet (Pass 3)

**Fichier** : `templates/ai/v2/pass3_planchet.j2`

**Mission** : Critiquer et valider. Produire un verdict.

**Entrées** :
- `event` : Événement perçu
- `briefing` : Contexte utilisateur
- `previous_passes` : Liste [Grimaud, Bazin]
- `context` : Contexte structuré

**Sorties** :
```json
{
  "critique": {
    "extraction_issues": ["..."],
    "action_issues": ["..."],
    "age_concerns": ["..."],
    "missing_elements": ["..."],
    "contradictions": ["..."]
  },
  "extractions": [...],
  "action": "...",
  "confidence": {...},
  "changes_from_bazin": ["..."],
  "questions_for_mousqueton": ["..."],
  "needs_mousqueton": false,
  "reasoning": "..."
}
```

**Questions à poser** :
1. Sur l'extraction — Manqué quelque chose ?
2. Sur l'action — Trop agressif ?
3. Sur l'âge — Encore pertinent ?
4. Sur la confiance — Pourquoi pas plus haute ?

**Arrêt** :
- Condition : `confidence > 90%`
- Résultat : Extractions de Planchet (pas Bazin)

### 3.4 Mousqueton (Pass 4)

**Fichier** : `templates/ai/v2/pass4_mousqueton.j2`

**Mission** : Écouter tous les avis, puis trancher.

**Entrées** :
- `event` : Événement perçu (contenu complet)
- `briefing` : Contexte utilisateur
- `previous_passes` : Liste [Grimaud, Bazin, Planchet]
- `full_context` : Contexte complet

**Sorties** :
```json
{
  "arbitrage": {
    "planchet_answers": [
      {"question": "...", "answer": "..."}
    ],
    "conflicts_resolved": [
      {"conflict": "...", "resolution": "...", "winner": "grimaud|bazin|contexte"}
    ],
    "age_decision": {
      "still_relevant": true,
      "reasoning": "..."
    }
  },
  "extractions": [...],
  "action": "...",
  "confidence": {...},
  "reasoning": "..."
}
```

**Décisions** :
1. Résoudre les questions de Planchet
2. Trancher les conflits entre valets
3. Décider sur la pertinence malgré l'âge
4. Produire le verdict final

**Toujours dernier** : Si confiance < 90%, recommander `action: "queue"`.

---

## 4. Sensibilité à l'âge

Chaque valet interprète l'âge différemment :

| Âge | Indicateur | Grimaud | Bazin | Planchet | Mousqueton |
|-----|------------|---------|-------|----------|------------|
| < 7 jours | ✨ Frais | Normal | Normal | Urgence ? | Normal |
| 7-30 jours | 📅 Récent | Vérifier deadlines | Vérifier mémoires | Deadlines passées ? | Vérifier pertinence |
| > 30 jours | ⚠️ ANCIEN | Obsolescence | Doublons ! | Pourquoi si tard ? | Décision malgré âge |

---

## 5. Sélection des modèles

### 5.1 Mode économique (défaut)

| Pass | Modèle | Coût/1000 emails |
|------|--------|------------------|
| Grimaud | Haiku | ~$1.40 |
| Bazin | Haiku | ~$1.90 |
| Planchet | Haiku | ~$1.50 |
| Mousqueton | Sonnet | ~$2.70 |
| **Total** | — | **~$7.50** |

### 5.2 Mode adaptatif (recommandé)

Escalade automatique si confiance < seuil :

```
Haiku → Sonnet → Opus
```

| Scénario | Distribution | Coût estimé |
|----------|--------------|-------------|
| Trivial (early_stop) | 20% | ~$0.30 |
| Simple (Haiku ×3) | 50% | ~$4.80 |
| Moyen (→ Sonnet) | 25% | ~$5.00 |
| Complexe (→ Opus) | 5% | ~$2.00 |
| **Total** | 100% | **~$12** |

---

## 6. Format des extractions

Structure commune à tous les valets :

```json
{
  "info": "Résumé condensé de l'information",
  "type": "fait|decision|engagement|deadline|evenement|relation|coordonnees|montant|reference|demande",
  "importance": "haute|moyenne|basse",
  "note_cible": "Nom canonique du projet/actif",
  "note_action": "enrichir|creer",
  "omnifocus": false,
  "calendar": false,
  "date": "YYYY-MM-DD ou null",
  "time": "HH:MM ou null",
  "duration": null
}
```

---

## 7. Mapping avec l'ancien système

| Ancien (v2.2) | Nouveau (v3.0) |
|---------------|----------------|
| `pass1_blind_extraction.j2` | `pass1_grimaud.j2` |
| `pass2_contextual_refinement.j2` | `pass2_bazin.j2` |
| — (nouveau) | `pass3_planchet.j2` |
| `pass4_deep_reasoning.j2` | `pass4_mousqueton.j2` |

---

## 8. Métriques et observabilité

### 8.1 Métriques à collecter

- `pass_count` : Nombre de passes par événement
- `early_stop_rate` : % d'arrêts à Grimaud
- `planchet_stop_rate` : % d'arrêts à Planchet
- `confidence_by_pass` : Distribution des confiances
- `model_escalation_rate` : % d'escalades de modèle
- `cost_per_event` : Coût moyen par événement

### 8.2 Alertes

- Si `early_stop_rate` > 50% : Vérifier qualité des suppressions
- Si `planchet_stop_rate` < 30% : Bazin/Planchet sous-performent
- Si `model_escalation_rate` > 40% : Revoir les seuils

---

## 9. Migration

### 9.1 Stratégie

1. **Phase 1** : Déployer en shadow mode (comparer avec v2.2)
2. **Phase 2** : A/B testing sur 10% du trafic
3. **Phase 3** : Rollout progressif
4. **Phase 4** : Décommissionner v2.2

### 9.2 Rollback

Conserver les anciens templates pendant 30 jours après migration complète.

---

## 10. Annexes

### 10.1 Références littéraires

> **Grimaud** : "Grimaud était d'un silence exemplaire. Athos l'avait habitué à ne répondre que par signes."
>
> **Bazin** : "Bazin était un homme de trente-cinq à quarante ans, gras, doux, béat, s'occupant à lire des livres pieux."
>
> **Planchet** : "Planchet était un garçon de Picardie, brave, serviable, mais surtout curieux."
>
> **Mousqueton** : "Mousqueton était un Normand dont le nom pacifique de Boniface avait été changé par son maître Porthos."

### 10.2 Fichiers

```
templates/ai/v2/
├── pass1_grimaud.j2      (220 lignes)
├── pass2_bazin.j2        (240 lignes)
├── pass3_planchet.j2     (224 lignes)
├── pass4_mousqueton.j2   (220 lignes)
└── [anciens fichiers conservés pour rollback]
```
