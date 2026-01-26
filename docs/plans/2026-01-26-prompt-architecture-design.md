# Architecture Modulaire des Prompts IA — Design v1

**Date** : 26 janvier 2026
**Statut** : Draft — En attente de review
**Auteur** : Johan + Claude

---

## Contexte et Problématique

### Constat initial

Scapin utilise l'IA pour deux missions principales :

1. **Analyse d'événements** (emails) — Pipeline multi-pass (Grimaud → Bazin → Planchet → Mousqueton)
2. **Retouche de notes** (mémoires) — Single-pass avec escalade de modèle

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

---

## Architecture proposée

### Structure des fichiers

```
templates/ai/
├── blocks/                        # BLOCS RÉUTILISABLES (cacheable)
│   ├── identity.j2                # Identité Scapin commune
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

## Ta mission : Retouche des notes

[Instructions spécifiques retouche...]

{% include 'blocks/note_types.j2' %}
{% include 'blocks/extraction_types.j2' %}
{% include 'blocks/confidence_calibration.j2' %}
{% include 'blocks/enrichment_sections.j2' %}
{% include 'blocks/json_response.j2' with context %}
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

### 2. `blocks/note_types.j2`

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

### 3. `blocks/extraction_types.j2`

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

### 4. `blocks/confidence_calibration.j2`

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

### 5. `blocks/enrichment_sections.j2`

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

### 6. `blocks/json_response.j2`

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

## Migration depuis l'existant

### Phase 1 : Créer les blocs communs
- Extraire les éléments communs des prompts existants
- Créer les fichiers `blocks/*.j2`
- Tester l'inclusion

### Phase 2 : Migrer la retouche
- Créer `retouche/system.j2` (remplace le hardcodé)
- Ajouter CoT et exemples
- Ajouter type "concept"
- Tester avec Haiku

### Phase 3 : Migrer l'analyse (optionnel)
- Refactorer les 4 passes pour utiliser les blocs
- Conserver la compatibilité

### Phase 4 : Validation
- Comparer qualité avant/après
- Mesurer taux d'escalade Haiku → Sonnet
- Ajuster si nécessaire

---

## Questions ouvertes

1. **Caching** : Les blocs inclus sont-ils correctement cachés par Anthropic ?
2. **Longueur** : Quelle est la limite pratique avant dégradation ?
3. **Exemples retouche** : Combien d'exemples few-shot sont optimaux ?
4. **CoT** : Le CoT augmente-t-il vraiment la qualité pour notre use case ?

---

## Prochaines étapes

- [ ] Review de ce design avec Johan
- [ ] Définir le contenu détaillé de chaque bloc
- [ ] Prototyper `retouche/system.j2` avec blocs
- [ ] Tester sur quelques notes réelles
- [ ] Mesurer l'impact sur la qualité et les coûts

---

*Document généré lors de la session de brainstorming du 26 janvier 2026*
