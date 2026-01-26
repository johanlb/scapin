# Architecture Modulaire des Prompts IA — Design v4

**Date** : 26 janvier 2026
**Statut** : Draft — Architecture Cloud + RAG Haute Capacité
**Auteur** : Johan + Claude

---

## Contexte et Problématique

### Constat initial

Scapin utilise l'IA pour deux missions principales :

1. **Analyse d'événements** (emails) — ~~Pipeline multi-pass 4 valets~~ → Nouveau : Haiku triage + Sonnet escalade
2. **Retouche de notes** (mémoires) — Single-pass avec escalade de modèle

> **Note** : Le pipeline 4-passes (anciens noms de passes : Grimaud, Bazin, Planchet, Mousqueton) est **déprécié**. Ces noms désignaient des étapes d'analyse dans Sancho, pas des modules. Aujourd'hui, "Grimaud" et "Bazin" désignent de **nouveaux modules** distincts (PKM Guardian et Briefings). L'architecture retenue est Cloud + RAG avec escalade Haiku → Sonnet.

Les prompts ont été développés organiquement, en commençant par l'analyse d'événements. La retouche a été ajoutée plus tard avec une architecture différente et moins élaborée.

### Problèmes identifiés

| Problème | Impact |
|----------|--------|
| **Asymétrie massive** | Analyse = 854 lignes de system prompts, Retouche = 80 lignes |
| **System prompt retouche hardcodé** | Dans `retouche_reviewer.py`, difficile à maintenir |
| **Pas de base commune** | Chaque mission réinvente l'identité Scapin, le format JSON, etc. |
| **Pas d'exemples en retouche** | Grimaud a 8 exemples complets, retouche = 0 |
| **Type "Concept" manquant** | Nouveau type de note non intégré |
| **Pas de Chain of Thought** | Technique de prompting non exploitée |
| **🔴 Canevas absent de retouche** | Contexte permanent de Johan non injecté dans la retouche |
| **Templates PKM non référencés** | Instructions Jinja2 redéfinissent la structure au lieu de référencer |

### Objectifs de la refonte

1. **Qualité** — Améliorer les résultats, surtout pour la retouche
2. **Maintenabilité** — Modifier un bloc impacte toutes les missions
3. **Coût** — Optimiser pour que Haiku réussisse (éviter l'escalade vers Sonnet/Opus)

---

## Principe économique fondamental

```
┌─────────────────────────────────────────────────────────┐
│  MAUVAISE OPTIMISATION                                  │
│  Prompt court → Haiku échoue → Escalade Sonnet          │
│  Coût : 0.25$ + 3$ = 3.25$                              │
├─────────────────────────────────────────────────────────┤
│  BONNE OPTIMISATION                                     │
│  Prompt complet → Haiku réussit → Pas d'escalade        │
│  Coût : 0.30$ = 0.30$                                   │
└─────────────────────────────────────────────────────────┘
```

**Règle** : Ne jamais sacrifier la qualité pour réduire les tokens. Un prompt plus long qui permet à Haiku de réussir coûte moins cher qu'un prompt court qui force l'escalade.

> **Voir aussi** : [Analyse économique détaillée](./2026-01-26-model-economics-analysis.md) — comparaison multi-fournisseur (Anthropic, OpenAI, Mistral, Google)

---

## Sources de contexte externe

### Canevas — Contexte permanent de Johan

Le **Canevas** est le contexte permanent injecté dans les prompts IA. Il permet à Scapin de comprendre qui est Johan, ses priorités, et comment interagir avec lui.

**Fichiers** (dans `Notes/Canevas/`) :

| Fichier | Contenu | Taille |
|---------|---------|--------|
| `Profile.md` | État civil, localisation, contacts, cercle proche, responsabilités | ~4k chars |
| `Projects.md` | Portfolio stratégique avec priorités (🔴 HIGH, 🟡 ACTIVE, 🔵 PERSONAL) | ~6k chars |
| `Goals.md` | Vision stratégique, North Star, objectifs par domaine, gardes psychologiques | ~8k chars |
| `Preferences.md` | Langue, horaires, préférences email, format documentation | ~1.5k chars |

**État actuel de l'injection** :

| Mission | Canevas injecté ? | Impact |
|---------|-------------------|--------|
| Analyse (Grimaud) | ✅ Oui | Comprend le contexte pour extraire |
| Analyse (Bazin) | ✅ Oui | Enrichit avec le bon contexte |
| Analyse (Planchet) | ✅ Oui | Planifie selon les priorités |
| Analyse (Mousqueton) | ✅ Oui | Arbitre avec la vision globale |
| **Retouche** | ❌ **NON** | 🔴 **GAP CRITIQUE** |

**Conséquences du gap** :
- La retouche ne connaît pas les projets actifs → mauvaise priorisation
- Les préférences de style ne guident pas la réécriture
- Le contexte relationnel manque pour évaluer l'importance d'une note
- Incohérence entre missions (analyse contextualisée, retouche aveugle)

**Solution** : Injecter le Canevas dans `retouche/system.j2` via un bloc dédié.

### Templates PKM — Structure des notes par type

Les **Templates** définissent la structure attendue pour chaque type de note. Ils sont stockés dans le PKM de Johan (Apple Notes) et chargés dynamiquement.

**Fichiers** (dans `Notes/Personal Knowledge Management/Modèles/`) :

| Template | Type de note | Sections clés |
|----------|--------------|---------------|
| `Modèle — Fiche Personne.md` | personne | Coordonnées, relation, profil relationnel, réciprocité |
| `Modèle — Fiche Projet.md` | projet | Objectif, opportunités, calendrier, tâches, risques |
| `Modèle — Fiche Entité.md` | entite | Admin, caractéristiques, propriétaires, financier |
| `Modèle — Fiche Réunion.md` | reunion | Participants, ordre du jour, décisions, actions |
| `Modèle — Fiche Processus.md` | processus | Objectif, prérequis, étapes, critères succès |
| `Modèle — Fiche Événement.md` | evenement | Dates, participants, programme, budget |

**Relation Templates ↔ Prompts Jinja2** :

```
┌─────────────────────────────────────────────────────────────────┐
│  APPROCHE RETENUE : RÉFÉRENCEMENT (pas de synchronisation)     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Templates PKM (Notes/)         Prompts Jinja2 (templates/ai/)  │
│  ─────────────────────         ───────────────────────────────  │
│                                                                 │
│  Définissent QUOI              Définissent COMMENT              │
│  (structure attendue)          (instructions d'évaluation)      │
│                                                                 │
│  ┌──────────────────┐          ┌──────────────────────────┐    │
│  │ Fiche Personne   │ ──────▶  │ retouche/personne.j2     │    │
│  │ - Coordonnées    │ injecté  │ "Vérifie que les sections │    │
│  │ - Relation       │ via      │  du template sont         │    │
│  │ - Profil         │ variable │  présentes et complètes"  │    │
│  └──────────────────┘          └──────────────────────────┘    │
│                                                                 │
│  Source unique de vérité       Instructions contextuelles       │
│  (modifiable par Johan)        (logique d'évaluation)           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Mécanisme actuel** :
1. `retouche_reviewer.py` charge le template via `TEMPLATE_TYPE_MAP`
2. Le contenu entre `━━━ DÉBUT/FIN MODÈLE ━━━` est extrait
3. Injecté dans le prompt via `{{ template_structure }}`
4. Le Jinja2 `retouche/types/*.j2` donne les instructions d'usage

**Règle** : Les fichiers `retouche/types/*.j2` ne doivent **jamais** redéfinir la structure — ils référencent le template injecté et donnent des instructions sur comment l'évaluer/appliquer.

---

## Architecture proposée

### Structure des fichiers

```
templates/ai/
├── blocks/                        # BLOCS RÉUTILISABLES (cacheable)
│   ├── identity.j2                # Identité Scapin commune
│   ├── canevas.j2                 # 🆕 Injection du contexte permanent Johan
│   ├── json_response.j2           # Structure JSON de réponse
│   ├── confidence_calibration.j2  # Règles de confiance 0-1
│   ├── extraction_types.j2        # fait, decision, engagement...
│   ├── note_types.j2              # personne, projet, entite, concept...
│   ├── pkm_rules.j2               # Règles d'écriture dans les notes
│   └── enrichment_sections.j2     # Sections d'enrichissement auto
│
├── analyse/                       # MISSION ANALYSE ÉVÉNEMENTS
│   ├── grimaud/
│   │   ├── system.j2              # Inclut blocks + règles Grimaud
│   │   └── user.j2
│   ├── bazin/
│   │   ├── system.j2
│   │   └── user.j2
│   ├── planchet/
│   │   ├── system.j2
│   │   └── user.j2
│   └── mousqueton/
│       ├── system.j2
│       └── user.j2
│
└── retouche/                      # MISSION RETOUCHE NOTES
    ├── system.j2                  # Inclut blocks + règles retouche
    ├── user.j2                    # Données de la note
    └── types/                     # Instructions par type de note
        ├── personne.j2
        ├── projet.j2
        ├── entite.j2
        ├── reunion.j2
        ├── evenement.j2
        ├── processus.j2
        ├── concept.j2             # NOUVEAU
        └── generique.j2
```

### Principe d'inclusion

Chaque system prompt inclut les blocs communs :

```jinja2
{# retouche/system.j2 #}
{% include 'blocks/identity.j2' %}

{# 🆕 Canevas injecté pour contexte permanent #}
{% include 'blocks/canevas.j2' %}

## Ta mission : Retouche des notes

[Instructions spécifiques retouche...]

{% include 'blocks/note_types.j2' %}
{% include 'blocks/extraction_types.j2' %}
{% include 'blocks/confidence_calibration.j2' %}
{% include 'blocks/enrichment_sections.j2' %}
{% include 'blocks/json_response.j2' with context %}
```

### Principe de référencement des templates

Les fichiers `retouche/types/*.j2` **référencent** le template PKM injecté :

```jinja2
{# retouche/types/personne.j2 #}
{# NE PAS redéfinir la structure — elle est dans {{ template_structure }} #}

## Instructions pour fiche Personne

Le template de référence est fourni dans "Modèle de référence" ci-dessus.

**Évaluation** :
- Vérifie que les sections obligatoires sont présentes (Coordonnées, Relation)
- Vérifie que le contenu est à jour (dates, contacts)
- Propose `structure` si la note ne suit pas le modèle
- Propose `enrich` si des sections sont vides mais pourraient être complétées

**Ne jamais** :
- Inventer des informations manquantes
- Supprimer les sections d'enrichissement automatique
- Restructurer une note bien organisée différemment du modèle
```

---

## Contenu des blocs communs

### 1. `blocks/identity.j2`

```jinja2
{# Identité commune Scapin — Cacheable #}

Tu es un valet de **Scapin**, l'assistant cognitif de Johan.

Scapin est un système qui aide Johan à :
- Traiter ses événements entrants (emails, messages)
- Maintenir sa base de connaissances personnelle (PKM)
- Prendre des décisions éclairées grâce au contexte

**Ton maître** : Johan Le Bail
**Ta mission** : Prendre soin de Johan mieux que Johan lui-même.

**Règles absolues** :
1. JAMAIS inventer d'information
2. Respecter le ton et style existant de Johan
3. Privilégier la concision et la précision
4. Confiance > 0.85 pour actions auto-applicables
```

### 2. `blocks/canevas.j2` 🆕

```jinja2
{# Contexte permanent de Johan — Chargé dynamiquement #}
{# Ce bloc est NON-cacheable car le contenu change #}

## Contexte de Johan (Canevas)

{% if canevas %}
{{ canevas }}
{% else %}
⚠️ Canevas non disponible — procéder avec prudence.
{% endif %}

**Utilisation du Canevas** :
- **Profile** : Qui est Johan, son cercle proche, ses responsabilités
- **Projects** : Projets actifs et leur priorité (🔴 HIGH, 🟡 ACTIVE, 🔵 PERSONAL)
- **Goals** : Vision stratégique, North Star, gardes psychologiques
- **Preferences** : Style de communication, horaires, préférences

**Pour la retouche** :
- Priorise les notes liées aux projets 🔴 HIGH PRIORITY
- Respecte le style direct et concis de Johan
- Tiens compte du contexte relationnel (cercle proche vs professionnel)
```

### 3. `blocks/note_types.j2`

```jinja2
{# Types de notes PKM — Cacheable #}

## Types de notes

| Type | Description | Exemples |
|------|-------------|----------|
| **personne** | Fiche contact | Ami, collègue, prestataire |
| **projet** | Projet en cours ou terminé | Vente Nautil 6, Migration serveur |
| **entite** | Organisation, lieu, bien | Société, copropriété, banque |
| **reunion** | Compte-rendu | Conseil AWCS, CODIR |
| **evenement** | Événement ponctuel | AG, voyage, anniversaire |
| **processus** | Procédure, workflow | Backup quotidien, revue GTD |
| **concept** | Idée, notion abstraite | Stratégie, framework, méthode |
| **souvenir** | Mémoire personnelle | Anecdote, moment vécu |
| **autre** | Non catégorisé | À trier |
```

### 4. `blocks/extraction_types.j2`

```jinja2
{# Types d'extraction — Cacheable #}

## Types d'information à extraire

| Type | Quand l'utiliser | Exemple |
|------|------------------|---------|
| **fait** | Information factuelle | "Marie promue directrice le 15/01" |
| **decision** | Choix validé | "Budget approuvé: 50k€" |
| **engagement** | Promesse, commitment | "Marc livrera lundi" |
| **deadline** | Échéance | "Rapport pour vendredi 18h" |
| **evenement** | Date/lieu | "Réunion Q2 le 15 janvier à Paris" |
| **relation** | Lien entre personnes/entités | "Marc rejoint Projet Alpha" |
| **coordonnees** | Contact | "Nouveau: 06 12 34 56 78" |
| **montant** | Valeur financière | "Contrat 50k€/an" |
| **reference** | Identifiant | "Facture #12345" |
| **demande** | Requête à traiter | "Peux-tu m'envoyer le rapport ?" |
```

### 5. `blocks/confidence_calibration.j2`

```jinja2
{# Calibration de confiance — Cacheable #}

## Calibration de la confiance

**Échelle** : 0.0 à 1.0

| Niveau | Valeur | Quand |
|--------|--------|-------|
| Très haute | 0.95+ | Contenu évident (OTP, spam), early stop possible |
| Haute | 0.85-0.95 | Contexte confirme, action auto-applicable |
| Moyenne | 0.70-0.85 | Confiance raisonnable, peut nécessiter review |
| Basse | 0.50-0.70 | Incertain, escalade ou question recommandée |
| Très basse | <0.50 | Doute majeur, ne pas agir |

**Règles** :
- Ne mets PAS 0.95+ sauf certitude absolue
- Préfère sous-estimer en cas de doute
- La confiance basse n'est pas un échec, c'est de l'honnêteté
```

### 6. `blocks/enrichment_sections.j2`

```jinja2
{# Sections d'enrichissement automatique — Cacheable #}

## Sections d'enrichissement (NE PAS SUPPRIMER)

Ces sections sont ajoutées automatiquement lors du traitement des événements.
Elles contiennent des informations traçables. **Ne jamais les supprimer.**

**Formats** :

### Engagements / Informations / Faits / Décisions / Jalons
```
## [Section]
- 🔴 **YYYY-MM-DD** : [contenu] — [source](scapin://event/xxx)
```
(🔴 = haute importance, 🟡 = moyenne, ⚪ = basse)

### Questions ouvertes
```
## Questions ouvertes
### ❓ [Question]
- **Catégorie** : [type]
- **Source** : [valet] (via email "[sujet]")
- **Ajoutée le** : YYYY-MM-DD
```

### Recherche Web
```
## Recherche Web
**[Titre]**
[Contenu...]
> Source: [URL]
```
```

### 7. `blocks/json_response.j2`

```jinja2
{# Format de réponse JSON — Paramétrable selon mission #}

## Format de réponse

Réponds en JSON valide uniquement.

```json
{
  {% if mission == 'analyse' %}
  "extractions": [...],
  "action": "archive|flag|queue|delete",
  "early_stop": false,
  "early_stop_reason": null,
  {% elif mission == 'retouche' %}
  "quality_score": 0-100,
  "actions": [...],
  {% endif %}
  "confidence": {
    "entity_confidence": 0.0-1.0,
    "action_confidence": 0.0-1.0,
    "extraction_confidence": 0.0-1.0,
    "completeness": 0.0-1.0
  },
  "reasoning": "Explication courte"
}
```
```

---

## Techniques de prompting à intégrer

### Chain of Thought (CoT)

**Où l'ajouter** : Retouche (décisions complexes sur restructuration)

**Format proposé** :

```jinja2
Avant de répondre, réfléchis étape par étape :

1. **Analyse** : Quel est le type de cette note ? Quel est son état actuel ?
2. **Diagnostic** : Quels sont les problèmes de qualité ?
3. **Priorisation** : Quelles actions auraient le plus d'impact ?
4. **Décision** : Quelles actions proposer avec quelle confiance ?

Ensuite seulement, produis ta réponse JSON.
```

### Few-shot examples

**Où les ajouter** : Retouche (actuellement 0 exemple)

**Exemples à créer** :

1. Note personne fragmentaire → action `structure` + `enrich`
2. Note projet bien structurée → action `score` uniquement
3. Note sans type → action `assign_type`
4. Note avec enrichissements → préservation des sections

---

## Architecture Cloud + RAG (Version Retenue)

### Décision architecturale

Après analyse, l'option **Cloud + RAG** a été retenue plutôt que le modèle local fine-tuné :

| Critère | Local Fine-tuné | Cloud + RAG |
|---------|-----------------|-------------|
| Confidentialité | ✅ Excellente | ✅ Acceptable (non critique) |
| Coût | ~$15-20/mois | ~$30-120/mois |
| Complexité | 🔴 Élevée (training, déploiement) | ✅ Simple |
| Maintenance | 🔴 Retraining régulier | ✅ Aucune |
| Qualité | 🟡 Limitée (8B) | ✅ Meilleure (Sonnet) |
| **Décision** | ❌ Abandonné | ✅ **Retenu** |

**Raison** : La confidentialité n'est pas critique pour Johan. Les coûts cloud sont acceptables (budget $200/mois). La simplicité prime.

### Architecture retenue

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ARCHITECTURE SCAPIN — CLOUD + RAG                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ PRÉPARATION CONTEXTE (pas d'IA, instantané)                         │    │
│  │                                                                     │    │
│  │ • Lookup expéditeur → Fiche contact si connue                       │    │
│  │ • FAISS top 5 → Notes similaires (embeddings toujours frais)        │    │
│  │ • Canevas → Toujours inclus (Profile, Projects, Goals, Preferences) │    │
│  │ • Template du type → Injecté pour retouche                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│          ┌─────────────────────────┼─────────────────────────┐              │
│          ▼                         ▼                         ▼              │
│  ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐      │
│  │ TIER 1 : TRIAGE   │   │ TIER 2 : ANALYSE  │   │ TIER 3 : CRITIQUE │      │
│  │ Haiku (cached)    │   │ Sonnet            │   │ Opus              │      │
│  │ $0.004/requête    │   │ $0.025/requête    │   │ $0.25+/requête    │      │
│  │                   │   │                   │   │                   │      │
│  │ • 80% des events  │   │ • 20% complexes   │   │ • Décisions       │      │
│  │ • Triage rapide   │   │ • Extraction fine │   │   stratégiques    │      │
│  │ • Early stop      │   │ • Retouche notes  │   │ • Raisonnement    │      │
│  │   (spam, OTP)     │   │ • Chat courant    │   │   multi-étapes    │      │
│  └───────────────────┘   └───────────────────┘   └───────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Ce que le RAG apporte (temps réel, toujours frais)

| Donnée | Source | Mise à jour |
|--------|--------|-------------|
| Contenu des notes | Apple Notes sync | < 1 min |
| État des projets | Notes PKM | < 1 min |
| Informations personnes | Fiches contact | < 1 min |
| Deadlines, engagements | Enrichissements | Temps réel |
| Canevas (Profile, Goals...) | Notes dédiées | Quand modifié |

**Pipeline de fraîcheur** :
```
Note modifiée → Sync Scapin → Re-embed (FAISS) → Disponible en <1 min
```

---

## Projections Haute Capacité

### Volume cible

Johan souhaite que Scapin monitore à terme :

| Source | Volume/jour | Volume/mois | Caractéristiques |
|--------|-------------|-------------|------------------|
| **Teams** | 200 | 6 000 | Messages courts, conversations |
| **Emails** (pro + perso) | 200 | 6 000 | Variable, threads |
| **WhatsApp** | 30 | 900 | Personnel, informel |
| **Transcriptions** | 5 | 150 | Long (10-60 min), dense |
| **Total** | **435** | **~13 000** | |

### Architecture multi-tier pour haute capacité

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PIPELINE HAUTE CAPACITÉ — 13 000 événements/mois                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  NIVEAU 0 : PRÉ-FILTRAGE (règles, $0)                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ • OTP, confirmations automatiques → Archiver direct                 │    │
│  │ • Notifications système → Ignorer                                   │    │
│  │ • Spam détecté → Poubelle                                           │    │
│  │ • Messages < 10 mots sans contexte → Skip                           │    │
│  │                                                                     │    │
│  │ 13 000 → ~6 500 (50% filtré)                                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                                    ▼                                        │
│  AGRÉGATION (pas d'IA)                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ • Grouper messages Teams par conversation (5-10 msg → 1 unité)      │    │
│  │ • Grouper emails par thread                                         │    │
│  │ • WhatsApp : par conversation/jour                                  │    │
│  │                                                                     │    │
│  │ 6 500 → ~3 000 unités d'analyse                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                                    ▼                                        │
│  NIVEAU 1 : TRIAGE HAIKU ($0.004/unité, cache activé)                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ • Classification : important / routine / bruit                      │    │
│  │ • Extraction rapide des entités mentionnées                         │    │
│  │ • Détection de deadlines, demandes                                  │    │
│  │                                                                     │    │
│  │ 80% traité ici (2 400 unités × $0.004 = $9.60)                       │    │
│  │ 20% escalade → Sonnet                                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                    ┌───────────────┴───────────────┐                        │
│                    ▼                               ▼                        │
│  NIVEAU 2 : SONNET — Events complexes       NIVEAU 2 : SONNET — Transcripts │
│  ┌─────────────────────────────┐            ┌─────────────────────────────┐ │
│  │ 600 unités × $0.025 = $15   │            │ 150 transcripts × $0.15 =   │ │
│  │                             │            │ $22.50                      │ │
│  │ • Extraction complète       │            │                             │ │
│  │ • Nuances relationnelles    │            │ • Résumé structuré          │ │
│  │ • Décisions implicites      │            │ • Extraction décisions      │ │
│  │ • Engagements subtils       │            │ • Actions assignées         │ │
│  └─────────────────────────────┘            │ • Points clés               │ │
│                                             └─────────────────────────────┘ │
│                                                                             │
│  NIVEAU 3 : OPUS (rare, ~20/mois × $0.25 = $5)                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ • Décisions stratégiques importantes                                │    │
│  │ • Arbitrage entre priorités conflictuelles                          │    │
│  │ • Raisonnement multi-facteurs complexe                              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Coût mensuel estimé (haute capacité)

| Niveau | Volume | Coût unitaire | Total |
|--------|--------|---------------|-------|
| Pré-filtrage (règles) | 13 000 | $0 | $0 |
| Haiku triage (80%) | 2 400 | $0.004 | $9.60 |
| Sonnet analyse (20%) | 600 | $0.025 | $15.00 |
| Sonnet transcripts | 150 | $0.15 | $22.50 |
| Opus stratégique | 20 | $0.25 | $5.00 |
| **Sous-total analyse** | | | **$52.10** |
| | | | |
| Retouche notes | 200 | $0.05 | $10.00 |
| Chat assistant | ~500 | $0.05 | $25.00 |
| Embeddings (re-index) | 1000 | $0.001 | $1.00 |
| **Sous-total autres** | | | **$36.00** |
| | | | |
| Marge de sécurité (+30%) | | | $26.40 |
| **TOTAL MENSUEL** | | | **~$117/mois** |

**Dans le budget** : $117 << $200 (budget max Johan)

### Avantages de cette architecture

| Aspect | Bénéfice |
|--------|----------|
| **Scalabilité** | 13x volume actuel sans changement d'architecture |
| **Coût maîtrisé** | ~$117/mois même à haute capacité |
| **Qualité** | Sonnet pour cas complexes (20%) garantit la précision |
| **Simplicité** | Pas de modèle local à maintenir |
| **Latence** | Pré-filtrage instantané, triage rapide |
| **Flexibilité** | Ajuster les seuils d'escalade selon qualité observée |

### Pipelines par source

#### Emails (6 000/mois)

```
Email → Pré-filtre (OTP, spam) → Haiku triage → [Simple: archive | Complexe: Sonnet]
```

#### Teams (6 000/mois)

```
Messages → Agrégation par conversation → Haiku triage → Extraction si pertinent
```

#### WhatsApp (900/mois)

```
Messages → Agrégation par conversation/jour → Haiku → Personnel: archive | Important: Sonnet
```

#### Transcriptions (150/mois)

```
Transcript → Toujours Sonnet ($0.15) → Résumé structuré + extractions → Enrichissement notes
```

---

## Flux de traitement détaillés

### Analyse d'événements (simplifié)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  NOUVEAU PIPELINE ANALYSE (1-2 étapes au lieu de 4)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ÉTAPE 0 : Préparation contexte (pas d'IA, instantané)                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ • Lookup expéditeur → Fiche contact si connue                       │    │
│  │ • FAISS top 5 → Notes similaires (embeddings toujours frais)        │    │
│  │ • Canevas → Toujours inclus                                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                                    ▼                                        │
│  ÉTAPE 1 : Triage Haiku (avec prompt caching)                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ • System prompt cacheable (Canevas + instructions)                  │    │
│  │ • Coût réduit de 90% sur tokens cachés                              │    │
│  │ • Classification + extraction rapide                                │    │
│  │ • Évalue si escalade nécessaire                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                    ┌───────────────┴───────────────┐                        │
│                    ▼                               ▼                        │
│  80% : Traitement terminé              20% : Escalade Sonnet               │
│  ┌─────────────────────────────┐      ┌─────────────────────────────┐      │
│  │ • Archive/Flag/Queue        │      │ • Extraction complète       │      │
│  │ • Enrichissement basique    │      │ • Nuances relationnelles    │      │
│  │ • Coût : $0.004             │      │ • Coût : $0.025             │      │
│  └─────────────────────────────┘      └─────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Retouche de notes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PIPELINE RETOUCHE (toujours Sonnet pour qualité d'écriture)                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Note à retoucher                                                           │
│       │                                                                     │
│       ├─→ Template du type (RAG)                                            │
│       ├─→ Notes liées (RAG)                                                 │
│       ├─→ Canevas (RAG) ← 🆕 GAP CORRIGÉ                                    │
│       │                                                                     │
│       ▼                                                                     │
│  Sonnet : Évalue + propose actions                                          │
│       │                                                                     │
│       ├─→ Score qualité ≥ 80 → Aucune action nécessaire                     │
│       │                                                                     │
│       └─→ Score qualité < 80 → Actions proposées (structure, enrich...)     │
│                                                                             │
│  Coût : ~$0.05/note (qualité d'écriture supérieure justifie le coût)        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Assistant Chat

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PIPELINE CHAT (RAG + Cloud)                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Question utilisateur                                                       │
│       │                                                                     │
│       ├─→ FAISS → Notes pertinentes (RAG temps réel)                        │
│       ├─→ Canevas (toujours)                                                │
│       │                                                                     │
│       ▼                                                                     │
│  Sonnet : Répond avec contexte frais                                        │
│       │                                                                     │
│       ├─→ Question factuelle → Réponse directe (~$0.03)                     │
│       │                                                                     │
│       ├─→ Question complexe → Réponse approfondie (~$0.10)                  │
│       │                                                                     │
│       └─→ Question stratégique critique → Opus (~$0.25)                     │
│                                                                             │
│  Coût estimé : ~$2.50/mois pour usage modéré (50 questions/mois)            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Migration depuis l'existant

### Phase 1 : Quick wins (prompts)

**Objectif** : Améliorer immédiatement la qualité sans changer l'architecture fondamentale.

- [ ] Créer les fichiers `blocks/*.j2` (blocs réutilisables)
- [ ] **Injecter le Canevas dans la retouche** — corriger le gap critique
- [ ] Refactorer `retouche/types/*.j2` pour référencer les templates PKM
- [ ] Ajouter type "concept"
- [ ] Créer template PKM "Concept" si nécessaire
- [ ] Activer prompt caching Anthropic pour réduire coûts

### Phase 2 : Simplification pipeline analyse

**Objectif** : Remplacer le pipeline 4-passes (déprécié) par Haiku triage + Sonnet escalade.

- [ ] Implémenter préparation contexte (lookup expéditeur, FAISS, Canevas)
- [ ] Haiku triage avec prompt caching
- [ ] Escalade Sonnet sur critères définis (confiance < 85%, complexité)
- [ ] Mesurer qualité et coût vs ancien pipeline
- [ ] Ajuster seuils d'escalade

### Phase 3 : Extension aux nouvelles sources

**Objectif** : Supporter Teams, WhatsApp, transcriptions.

| Source | Actions |
|--------|---------|
| Teams | Connecteur API, agrégation par conversation, filtre bruit |
| WhatsApp | Import historique, agrégation par jour/conversation |
| Transcriptions | Parser audio→texte, pipeline Sonnet dédié |

- [ ] Pré-filtrage par règles (OTP, spam, notifications)
- [ ] Agrégation intelligente (threads, conversations)
- [ ] Dashboard monitoring par source

### Phase 4 : Assistant Chat

**Objectif** : Interface conversationnelle avec le PKM.

- [ ] Endpoint chat dans l'API
- [ ] Interface UI dans le panneau latéral
- [ ] RAG temps réel (FAISS + Canevas)
- [ ] Escalade Opus pour questions stratégiques

### Phase 5 : Optimisation continue

- [ ] Ajuster seuils de confiance selon données réelles
- [ ] Dashboard coûts par source et par modèle
- [ ] Alertes si coût mensuel > seuil
- [ ] Métriques qualité (précision, recall par type d'extraction)

---

## Questions ouvertes

### Résolues par le brainstorm ✅

| Question | Décision |
|----------|----------|
| Architecture 4 valets optimale ? | ❌ Non — contexte dès le départ, 1-2 passes |
| Multi-fournisseur ? | ✅ Oui — Haiku + Sonnet + Opus |
| Modèle local fine-tuné ? | ❌ Abandonné — complexité non justifiée |
| Nombre de passes ? | 1-2 selon confiance (Haiku → Sonnet) |
| Canevas en retouche ? | ✅ Oui — gap critique à corriger |
| Budget acceptable ? | ✅ Jusqu'à $200/mois |
| Confidentialité critique ? | ❌ Non — cloud acceptable |
| Haute capacité supportée ? | ✅ ~13 000 events/mois → ~$117/mois |

### Questions restantes

1. **Seuils de confiance** : 85% pour escalade est-il le bon seuil ? (à calibrer sur données réelles)
2. **Template "Concept"** : Faut-il créer un template PKM pour le nouveau type ?
3. **Agrégation Teams** : Quelle fenêtre temporelle pour grouper les messages ? (5 min ? 30 min ?)
4. **Transcriptions** : Faut-il un prompt spécialisé ou réutiliser l'analyse standard ?
5. **Monitoring coûts** : Alerter à quel seuil ? ($100 ? $150 ?)

---

## Prochaines étapes

### Validé ✅

- [x] Review de ce design avec Johan (v2, v3)
- [x] Documenter le gap Canevas
- [x] Clarifier la relation Templates PKM ↔ Prompts Jinja2
- [x] Challenger architecture 4 valets → décision : pipeline simplifié
- [x] Analyser économie multi-modèle → Haiku (cached) + Sonnet + Opus
- [x] Évaluer modèle local fine-tuné → abandonné (complexité non justifiée)
- [x] Définir architecture haute capacité → 13 000 events/mois supportés
- [x] Valider budget → ~$117/mois << $200 max

### À faire — Court terme (Phase 1)

- [ ] Injecter Canevas dans retouche (quick win)
- [ ] Activer prompt caching Anthropic
- [ ] Créer template PKM "Concept"
- [ ] Créer les fichiers `blocks/*.j2`

### À faire — Moyen terme (Phase 2)

- [ ] Simplifier pipeline analyse (Haiku triage → Sonnet escalade)
- [ ] Mesurer qualité vs ancien pipeline 4-passes
- [ ] Calibrer seuils d'escalade

### À faire — Long terme (Phases 3-5)

- [ ] Connecteurs Teams, WhatsApp, transcriptions
- [ ] Pré-filtrage et agrégation intelligente
- [ ] Assistant chat avec RAG
- [ ] Dashboard monitoring coûts et qualité

---

**Documents liés** :
- [Analyse économique des modèles](./2026-01-26-model-economics-analysis.md)

---

*Document initié le 26 janvier 2026 — v4 Architecture Cloud + RAG Haute Capacité*
