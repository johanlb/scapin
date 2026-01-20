# Architecture des Quatre Valets — Spécification v3.0

**Date** : 2026-01-20
**Auteur** : Johan / Claude
**Status** : Draft

---

## 1. Vue d'ensemble

L'architecture "Quatre Valets" est une évolution du système multi-pass v2.2, orchestrée par **Sancho**. Inspirée des valets des Trois Mousquetaires de Dumas, elle crée un dialogue coopératif et contradictoire entre quatre personas distincts.

### 1.0 Sancho — L'orchestrateur

**Sancho** (`src/sancho/`) est le module de raisonnement IA de Scapin. Il orchestre l'analyse multi-pass en invoquant les quatre valets dans l'ordre.

```
┌────────────────────────────────────────────────────────┐
│                      SANCHO                             │
│            (Module de raisonnement IA)                  │
│                                                         │
│  Responsabilités :                                      │
│  • Orchestrer le pipeline Four Valets                   │
│  • Gérer les arrêts précoces (early_stop, confidence)  │
│  • Sélectionner les modèles par valet                   │
│  • Agréger les résultats finaux                         │
│                                                         │
│  Fichier : src/sancho/multi_pass_analyzer.py           │
└────────────────────────────────────────────────────────┘
```

Sancho utilise :
- **TemplateRenderer** : Génère les prompts pour chaque valet
- **AnthropicProvider** : Appelle l'API Claude (Haiku/Sonnet/Opus)
- **ContextSearcher** : Récupère le contexte via Passepartout

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
    "notes_used": ["Marc Dupont", "Projet Alpha"],
    "notes_ignored": ["Factures 2024 — hors sujet"],
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
0. TRIER — Filtrer les notes non pertinentes (→ `notes_ignored`)
1. IDENTIFIER — Résoudre les ambiguïtés de noms (→ `notes_used`)
2. VÉRIFIER — Détecter les doublons
3. ENRICHIR — Ajouter le contexte manquant
4. PRÉPARER — `memory_hint` pour Passepartout
5. AJUSTER — Adapter les actions (omnifocus, calendar)
6. ÉVALUER — Mettre à jour la confiance

**Filtrage du contexte** :
- Les notes fournies par Passepartout sont des **candidates** (pas toutes pertinentes)
- Bazin doit explicitement trier : `notes_used` vs `notes_ignored`
- Cela évite que des notes non pertinentes influencent l'analyse

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

## 5. Paramètres API par valet

### 5.1 Configuration recommandée

| Valet | Modèle (défaut) | Température | top_p | max_tokens |
|-------|-----------------|-------------|-------|------------|
| **Grimaud** | Haiku | 0.1 | 0.9 | 1500 |
| **Bazin** | Haiku | 0.2 | 0.9 | 2000 |
| **Planchet** | Haiku | 0.3 | 0.9 | 2000 |
| **Mousqueton** | Sonnet | 0.2 | 0.9 | 2500 |

**Justification** :
- **Grimaud (0.1)** : Extraction factuelle, peu de marge d'interprétation
- **Bazin (0.2)** : Enrichissement, légère flexibilité pour connexions
- **Planchet (0.3)** : Critique, besoin d'un peu de réflexion créative
- **Mousqueton (0.2)** : Arbitrage, mais décision ferme et cohérente

### 5.2 Configuration YAML

```yaml
sancho:
  four_valets:
    enabled: true

    api_params:
      grimaud:
        model: haiku
        temperature: 0.1
        top_p: 0.9
        max_tokens: 1500
      bazin:
        model: haiku
        temperature: 0.2
        top_p: 0.9
        max_tokens: 2000
      planchet:
        model: haiku
        temperature: 0.3
        top_p: 0.9
        max_tokens: 2000
      mousqueton:
        model: sonnet
        temperature: 0.2
        top_p: 0.9
        max_tokens: 2500

    stopping_rules:
      grimaud_early_stop_confidence: 0.95
      planchet_stop_confidence: 0.90
      mousqueton_queue_confidence: 0.90

    adaptive_escalation:
      enabled: true
      threshold: 0.80
      escalation_map:
        haiku: sonnet
        sonnet: opus
```

---

## 6. Sélection des modèles

### 6.1 Mode économique (défaut)

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

## 7. Écriture dans les mémoires

### 7.1 Responsabilités

| Composant | Rôle |
|-----------|------|
| **Passepartout** | Fournit les notes candidates (retrieval) |
| **Bazin** | Filtre (`notes_ignored`) + Prépare : `note_cible`, `section_cible`, `format_suggere` |
| **Planchet** | Valide : note existe ? section correcte ? pas doublon ? |
| **Mousqueton** | Finalise : `ready_for_passepartout: true` |
| **Passepartout** | Exécute l'écriture réelle dans les notes PKM |

### 7.2 Structure `memory_hint`

Chaque extraction contient un `memory_hint` pour guider Passepartout :

```json
{
  "memory_hint": {
    "section_cible": "## Budget",
    "format_suggere": "bullet_date",
    "contexte_existant": "Budget Q1: 30k€",
    "validation": "ok",
    "ready_for_passepartout": true
  }
}
```

| Champ | Description | Valeurs |
|-------|-------------|---------|
| `section_cible` | Section de la note où écrire | `## Historique`, `## Contacts`, etc. |
| `format_suggere` | Format de l'entrée | `bullet`, `bullet_date`, `paragraphe`, `tableau` |
| `contexte_existant` | Ce qui existe déjà (pour éviter doublons) | Texte libre |
| `validation` | Statut de validation par Planchet | `ok`, `corrige`, `doublon_ignore` |
| `ready_for_passepartout` | Prêt pour écriture (Mousqueton only) | `true`, `false` |

### 7.3 Filtrage du contexte (Bazin)

Passepartout fournit des notes **candidates** basées sur la similarité sémantique.
Bazin doit les trier car certaines peuvent être des faux positifs :

```
Passepartout (retrieval)
    │
    ├── Notes candidates (relevance > seuil)
    │
    ▼
Bazin (filtrage sémantique)
    │
    ├── notes_used: ["Projet Alpha", "Marc Dupont"]
    ├── notes_ignored: ["Factures 2024 — hors sujet"]
    │
    ▼
Analyse enrichie (sans bruit)
```

**Pourquoi ce filtrage ?**
- Les embeddings peuvent matcher sur des mots similaires mais contextes différents
- Une note "Marc Dupont" comptable ≠ "Marc Dupont" développeur
- Bazin voit le contenu et peut juger la vraie pertinence

### 7.4 Flux d'écriture

```
Valet final (Planchet ou Mousqueton)
    │
    ├── extractions avec memory_hint
    │
    ▼
Passepartout
    │
    ├── Vérifie que note_cible existe
    ├── Localise section_cible
    ├── Applique format_suggere
    └── Écrit dans la note PKM
```

---

## 8. Format des extractions

Structure commune à tous les valets :

```json
{
  "info": "Résumé condensé de l'information",
  "type": "fait|decision|engagement|deadline|evenement|relation|coordonnees|montant|reference|demande",
  "importance": "haute|moyenne|basse",
  "note_cible": "Nom canonique du projet/actif",
  "note_action": "enrichir|creer",
  "memory_hint": {
    "section_cible": "## Section de la note",
    "format_suggere": "bullet|bullet_date|paragraphe|tableau",
    "validation": "ok|corrige|doublon_ignore",
    "ready_for_passepartout": true
  },
  "omnifocus": false,
  "calendar": false,
  "date": "YYYY-MM-DD ou null",
  "time": "HH:MM ou null",
  "duration": null
}
```

---

## 9. Mapping avec l'ancien système

| Ancien (v2.2) | Nouveau (v3.0) |
|---------------|----------------|
| `pass1_blind_extraction.j2` | `pass1_grimaud.j2` |
| `pass2_contextual_refinement.j2` | `pass2_bazin.j2` |
| — (nouveau) | `pass3_planchet.j2` |
| `pass4_deep_reasoning.j2` | `pass4_mousqueton.j2` |

---

## 10. Infrastructure existante

L'implémentation des Quatre Valets s'appuie sur l'infrastructure Sancho existante :

| Composant | Fichier | Description |
|-----------|---------|-------------|
| **TemplateRenderer** | `src/sancho/template_renderer.py` | Rendu Jinja2 avec filtres (`truncate_smart`, `format_date`) |
| **MultiPassAnalyzer** | `src/sancho/multi_pass_analyzer.py` | Orchestrateur avec `DecomposedConfidence` |
| **AnthropicProvider** | `src/sancho/providers/anthropic_provider.py` | API Claude (Haiku/Sonnet/Opus) |
| **ContextSearcher** | `src/sancho/context_searcher.py` | Coordination avec Passepartout |
| **Configuration** | `config/defaults.yaml` | YAML + Pydantic |

---

## 11. Métriques et observabilité

### 11.1 Métriques à collecter

- `pass_count` : Nombre de passes par événement
- `early_stop_rate` : % d'arrêts à Grimaud
- `planchet_stop_rate` : % d'arrêts à Planchet
- `confidence_by_pass` : Distribution des confiances
- `model_escalation_rate` : % d'escalades de modèle
- `cost_per_event` : Coût moyen par événement

### 11.2 Alertes

- Si `early_stop_rate` > 50% : Vérifier qualité des suppressions
- Si `planchet_stop_rate` < 30% : Bazin/Planchet sous-performent
- Si `model_escalation_rate` > 40% : Revoir les seuils

---

## 12. Migration

### 12.1 Stratégie

1. **Phase 1** : Déployer en shadow mode (comparer avec v2.2)
2. **Phase 2** : A/B testing sur 10% du trafic
3. **Phase 3** : Rollout progressif
4. **Phase 4** : Décommissionner v2.2

### 12.2 Rollback

Conserver les anciens templates pendant 30 jours après migration complète.

---

## 13. Calibration de confiance

Chaque valet a des règles de calibration pour éviter la sur-confiance :

### 13.1 Grimaud (Pass 1)
| Situation | Confiance |
|-----------|-----------|
| Contenu éphémère évident (OTP, spam) | 95-99% |
| Extraction normale sans contexte | 60-80% |
| Doute sur entité/projet | 50-70% |

### 13.2 Bazin (Pass 2)
| Situation | Confiance |
|-----------|-----------|
| Contexte confirmant tout | 85-95% |
| Contexte partiel | 75-85% |
| Contradictions détectées | 60-75% |

### 13.3 Planchet (Pass 3)
| Situation | Confiance |
|-----------|-----------|
| Tout validé, pas de problème | 91-95% → `needs_mousqueton: false` |
| Petits ajustements faits | 85-91% |
| Problèmes non résolus | 70-85% → `needs_mousqueton: true` |

### 13.4 Mousqueton (Pass 4)
| Situation | Confiance |
|-----------|-----------|
| Tous conflits résolus | 92-98% |
| Résolu mais incertitudes mineures | 90-92% |
| Problèmes non résolus | < 90% → `action: "queue"` |

---

## 14. Améliorations qualité (P0/P1)

### 14.1 P0 — Calibration confiance
- Instructions explicites de calibration dans chaque prompt
- Règle : "Sois HONNÊTE, pas optimiste"
- Préférer sous-estimer que sur-estimer

### 14.2 P1 — Few-shot examples
- Exemple OTP dans Grimaud pour `early_stop`
- Montre le comportement attendu

### 14.3 P1 — Validation JSON
- Instruction "AVANT DE RÉPONDRE : Vérifie que ton JSON est valide"
- Présent dans tous les prompts

### 14.4 P1 — Paramètres API
Voir section 5 pour les températures et top_p par valet.

---

## 15. Annexes

### 15.1 Références littéraires

> **Grimaud** : "Grimaud était d'un silence exemplaire. Athos l'avait habitué à ne répondre que par signes."
>
> **Bazin** : "Bazin était un homme de trente-cinq à quarante ans, gras, doux, béat, s'occupant à lire des livres pieux."
>
> **Planchet** : "Planchet était un garçon de Picardie, brave, serviable, mais surtout curieux."
>
> **Mousqueton** : "Mousqueton était un Normand dont le nom pacifique de Boniface avait été changé par son maître Porthos."

### 15.2 Fichiers de prompts

```
templates/ai/v2/
├── pass1_grimaud.j2      (~230 lignes) - Extraction silencieuse
├── pass2_bazin.j2        (~280 lignes) - Enrichissement contextuel
├── pass3_planchet.j2     (~240 lignes) - Critique et validation
├── pass4_mousqueton.j2   (~230 lignes) - Arbitrage final
│
├── [Anciens - conservés pour rollback]
├── pass1_blind_extraction.j2
├── pass2_contextual_refinement.j2
└── pass4_deep_reasoning.j2
```

### 15.3 Checklist des fonctionnalités

| Fonctionnalité | Grimaud | Bazin | Planchet | Mousqueton |
|----------------|---------|-------|----------|------------|
| Briefing | ✅ | ✅ | ✅ | ✅ |
| Sensibilité âge | ✅ | ✅ | ✅ | ✅ |
| Calibration confiance | ✅ | ✅ | ✅ | ✅ |
| Validation JSON | ✅ | ✅ | ✅ | ✅ |
| Few-shot example | ✅ (OTP) | — | — | — |
| Early stop | ✅ | — | — | — |
| Filtrage contexte | — | ✅ (`notes_ignored`) | — | — |
| memory_hint | — | ✅ | ✅ | ✅ |
| Extractions | ✅ | ✅ | ✅ | ✅ |
| Questions next pass | ✅ | ✅ | ✅ | — |

### 15.4 Terminologie Scapin

| Terme générique | Terme Scapin |
|-----------------|--------------|
| Email | Événement perçu / Péripétie |
| Notes PKM | Mémoires |
| Archives | Mémoires |
| Base de connaissances | Mémoires |
| Orchestrateur IA | Sancho |
| Pass | Valet |
| Extraction | Extraction |
| Action | Action |
