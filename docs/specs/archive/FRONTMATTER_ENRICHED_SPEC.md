# Frontmatter Enrichi — Spécification Contexte IA

**Status**: DRAFT
**Date**: 2026-01-17
**Auteur**: Johan + Claude
**Version**: 1.0

---

## 1. Résumé

Cette spécification définit les champs de frontmatter enrichis permettant à l'IA d'avoir une **meilleure compréhension du contexte** lors de l'analyse des événements entrants (emails, fichiers, invitations, etc.).

### 1.1 Objectif Principal

> *"Le rôle le plus important des notes est de permettre la meilleure compréhension possible du contexte par l'IA pour chaque événement entrant."*

### 1.2 Principes

| Principe | Description |
|----------|-------------|
| **IA propose, Johan valide** | L'IA suggère les valeurs, l'utilisateur approuve |
| **Flexibilité** | Pas de schéma rigide, tolérer les variations |
| **Préservation** | Le frontmatter survit aux syncs Apple Notes |
| **Enrichissement continu** | Workflows background maintiennent les données à jour |

---

## 2. Catégories de Champs

### 2.1 Comportements

| Catégorie | Comportement | Exemples |
|-----------|--------------|----------|
| **Auto-update** | Mis à jour sans validation | `last_contact`, `updated_at`, `mention_count` |
| **Propose & Validate** | Workflow propose, Johan valide | `role`, `email`, `phone`, `projects`, `relation` |
| **Manual only** | Jamais modifié automatiquement | `importance`, `notes_personnelles` |

### 2.2 Champ `pending_updates`

Les propositions en attente de validation sont stockées dans le frontmatter :

```yaml
pending_updates:
  - field: email
    value: "hugues@oceanrivervilla.mu"
    source: "email_signature"
    source_ref: "msg_id_12345"
    detected_at: 2026-01-17T10:30:00
    confidence: 0.92
  - field: role
    value: "CEO"
    source: "email_content"
    source_ref: "msg_id_67890"
    detected_at: 2026-01-17T11:00:00
    confidence: 0.85
```

---

## 3. Champs Universels (tous types de notes)

```yaml
---
# === IDENTIFICATION ===
title: "Nom de la note"
type: personne | projet | entite | reunion | evenement | processus | souvenir | autre
aliases: ["JLB", "Johan", "johanlb"]  # Noms alternatifs pour matching

# === MÉTADONNÉES SYSTÈME ===
created_at: 2025-12-27T17:16:59+00:00
updated_at: 2026-01-17T14:31:28+00:00
source: apple_notes | scapin | manual
source_id: "x-coredata://..."  # ID source externe si applicable

# === CLASSIFICATION ===
importance: haute | moyenne | basse  # Manual only
tags: [maurice, immobilier, investissement]
category: work | personal | finance | health | family | other

# === RELATIONS ===
related: ["[[Note Liée 1]]", "[[Note Liée 2]]"]

# === SOURCES LIÉES (pour enrichissement background) ===
linked_sources:
  - type: folder
    path: ~/Documents/Projets/Anahita
    priority: 1
  - type: whatsapp
    contact: "Équipe Anahita"
    priority: 2
  - type: email
    filter: "from:@anahita.com"
    priority: 2

# === PROPOSITIONS EN ATTENTE ===
pending_updates: []
---
```

---

## 4. Champs par Type de Note

### 4.1 PERSONNE

```yaml
---
title: Hugues Lagesse
type: personne
aliases: [Hugues, H. Lagesse, "Mr Lagesse"]
importance: haute

# === IDENTITÉ ===
first_name: Hugues
last_name: Lagesse
full_name: Hugues Lagesse

# === RELATION AVEC JOHAN ===
relation: partenaire  # ami, famille, collègue, client, partenaire, fournisseur, connaissance
relationship_strength: forte  # forte, moyenne, faible, nouvelle
introduced_by: "[[Damien Le Bail]]"  # Comment on s'est connus

# === PROFESSIONNEL ===
organization: "[[Ocean River Villa]]"
role: Directeur général
sector: immobilier

# === COMMUNICATION ===
email: hugues@example.com
phone: "+230 5XXX XXXX"
preferred_language: français
communication_style: formel  # formel, casual, technique
timezone: Indian/Mauritius

# === CONTEXTE ===
projects: ["[[Projet Immobilier Maurice]]"]
last_contact: 2026-01-15  # Auto-updated
mention_count: 12  # Auto-updated
first_contact: 2024-06-15

# === NOTES PERSONNELLES (Manual only) ===
notes_personnelles: "Préfère les appels aux emails. Très réactif."
---
```

### 4.2 PROJET

```yaml
---
title: Projet Immobilier Maurice
type: projet
aliases: [Ocean River Villa, ORV, Maurice Immo, "Projet Maurice"]
importance: haute

# === ÉTAT ===
status: actif  # actif, en_pause, terminé, annulé
priority: haute
domain: immobilier

# === TEMPORALITÉ ===
start_date: 2024-06-01
target_date: 2027-12-31
deadline: null  # Date butoir ferme si applicable

# === PARTIES PRENANTES ===
stakeholders:
  - person: "[[Johan Le Bail]]"
    role: investisseur
  - person: "[[Damien Le Bail]]"
    role: investisseur
  - person: "[[Hugues Lagesse]]"
    role: partenaire local
  - person: "[[Valerie Lincoln]]"
    role: banquière

# === FINANCIER ===
budget_range: ">100k€"
currency: EUR

# === CONTEXTE ===
related_entities: ["[[Ocean River Villa]]", "[[Azuri]]"]
last_activity: 2026-01-15  # Auto-updated
activity_count: 45  # Auto-updated
---
```

### 4.3 ENTITE (Organisation)

```yaml
---
title: Eufonie
type: entite
aliases: [Eufonie SAS, eufonie.fr, "Eufonie Consulting"]
importance: critique

# === TYPE D'ORGANISATION ===
entity_type: entreprise  # entreprise, administration, association, institution
sector: consulting IT
industry: technologie

# === RELATION ===
relationship: employeur  # employeur, client, fournisseur, partenaire, administration

# === CONTACTS CLÉS ===
contacts:
  - person: "[[Johan Le Bail]]"
    role: co-fondateur
  - person: "[[Damien Le Bail]]"
    role: communication

# === COORDONNÉES ===
website: https://eufonie.fr
email_domain: eufonie.fr
address: null
country: France

# === CONTEXTE ===
projects: ["[[Infrastructure Cloud]]"]
last_interaction: 2026-01-17  # Auto-updated
---
```

### 4.4 REUNION

```yaml
---
title: Point projet Maurice - 15 jan 2026
type: reunion
importance: normale

# === TEMPORALITÉ ===
date: 2026-01-15T14:00:00
duration_minutes: 60
timezone: Europe/Paris

# === LIEU ===
location: Teams
location_type: online  # online, physical, hybrid
meeting_url: "https://teams.microsoft.com/..."

# === PARTICIPANTS ===
participants:
  - person: "[[Johan Le Bail]]"
    role: organisateur
  - person: "[[Hugues Lagesse]]"
    role: participant
  - person: "[[Damien Le Bail]]"
    role: participant

# === CONTEXTE ===
project: "[[Projet Immobilier Maurice]]"
agenda: ["Revue budget", "Planning Q1", "Points ouverts"]

# === RÉSULTATS (post-réunion) ===
decisions: []
action_items: []
next_meeting: null
---
```

### 4.5 ACTIF / DOMAINE

```yaml
---
title: Nautil 6
type: actif
aliases: [N6, "Appartement Azuri"]
importance: haute

# === TYPE D'ACTIF ===
asset_type: bien_immobilier  # bien_immobilier, véhicule, investissement, domaine_expertise
asset_category: appartement

# === LOCALISATION ===
location: "Azuri Ocean & Golf Village"
address: "Nautil 6, Haute Rive, Maurice"
country: Maurice

# === VALEUR ===
acquisition_date: 2018-03-15
acquisition_value: null  # Optionnel
current_status: loué  # possédé, loué, en_vente, vendu

# === OPÉRATIONS ===
operations:
  - type: location
    section: "## Location"
  - type: charges
    section: "## Charges copropriété"
  - type: maintenance
    section: "## Maintenance"

# === CONTACTS LIÉS ===
contacts:
  - person: "[[Gestionnaire Azuri]]"
    role: syndic
  - person: "[[Locataire actuel]]"
    role: locataire

# === PROJETS LIÉS ===
projects: ["[[Projet Vente Nautil 6]]"]
---
```

---

## 5. Workflows Background d'Enrichissement

### 5.1 Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                    SOURCES D'INFORMATION                     │
│  Emails, Calendar, Teams, WhatsApp, Files, Web...           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              WORKFLOWS BACKGROUND (Passepartout)             │
│                                                              │
│  • Contact Tracker    → last_contact, mention_count          │
│  • Signature Parser   → email, phone, role, organization     │
│  • Project Linker     → projects, related                    │
│  • Relationship Inferrer → relation, relationship_strength   │
│  • Alias Discoverer   → aliases                              │
│  • Role Detector      → role, sector                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     NOTE MARKDOWN                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ --- (FRONTMATTER)                                      │ │
│  │ last_contact: 2026-01-17  ← AUTO-UPDATED               │ │
│  │ pending_updates:          ← PROPOSITIONS               │ │
│  │   - field: role                                        │ │
│  │     value: "CEO"                                       │ │
│  │ ---                                                    │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    VALIDATION JOHAN                          │
│  UI: "3 mises à jour proposées pour Hugues Lagesse"         │
│  [✓] last_contact → 2026-01-17 (auto-appliqué)              │
│  [ ] role → "CEO" (en attente validation)                   │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Workflows Détaillés

| Workflow | Source | Champs mis à jour | Comportement |
|----------|--------|-------------------|--------------|
| **Contact Tracker** | Emails, Teams | `last_contact`, `mention_count`, `first_contact` | Auto-update |
| **Signature Parser** | Emails | `email`, `phone`, `role`, `organization` | Propose & Validate |
| **Project Linker** | Tous | `projects`, `related`, `stakeholders` | Propose & Validate |
| **Relationship Inferrer** | Emails, Calendar | `relation`, `relationship_strength`, `introduced_by` | Propose & Validate |
| **Alias Discoverer** | Emails | `aliases` | Propose & Validate |
| **Role Detector** | Emails, LinkedIn | `role`, `sector`, `entity_type` | Propose & Validate |
| **Timeline Updater** | Tous | `last_activity`, `activity_count` | Auto-update |

### 5.3 Priorités d'Enrichissement

Les workflows priorisent les champs manquants :

```python
ENRICHMENT_PRIORITY = {
    # Critique pour le matching IA
    "aliases": 1,
    "relation": 1,
    "projects": 1,

    # Important pour le contexte
    "organization": 2,
    "role": 2,
    "stakeholders": 2,

    # Utile mais secondaire
    "email": 3,
    "phone": 3,
    "timezone": 3,

    # Auto-updated (pas de priorité)
    "last_contact": None,
    "mention_count": None,
}
```

---

## 6. Utilisation par l'IA

### 6.1 Matching Amélioré

**Avant** (sans aliases) :
```
Email de "Hugues" → recherche "Hugues" → 0 résultat
```

**Après** (avec aliases) :
```
Email de "Hugues"
  → recherche "Hugues"
  → match aliases ["Hugues", "H. Lagesse"]
  → trouve "Hugues Lagesse" ✅
```

### 6.2 Contexte Enrichi

**Avant** (frontmatter minimal) :
```
L'IA sait: "Hugues Lagesse" existe
```

**Après** (frontmatter enrichi) :
```
L'IA sait:
- Hugues Lagesse est un partenaire (relation: partenaire)
- Importance haute pour Johan
- Impliqué dans Projet Immobilier Maurice
- Organisation: Ocean River Villa (CEO)
- Dernier contact: il y a 2 jours
- Préfère le français, style formel
```

### 6.3 Prompt Enrichi

Le template d'extraction peut utiliser ces métadonnées :

```jinja2
{% for note in context_notes %}
## Note: {{ note.title }}
- Type: {{ note.frontmatter.type }}
- Relation: {{ note.frontmatter.relation | default('inconnue') }}
- Importance: {{ note.frontmatter.importance | default('normale') }}
- Projets: {{ note.frontmatter.projects | join(', ') | default('aucun') }}
- Dernier contact: {{ note.frontmatter.last_contact | default('inconnu') }}
{% endfor %}
```

---

## 7. Compatibilité Apple Notes

### 7.1 Smart Merge

Le sync Apple Notes préserve le frontmatter via "Smart Merge" :

```python
# Dans notes_sync.py - _format_scapin_note()
# Merge strategy:
# - Apple overwrites: title, apple_id, apple_folder, created, modified, synced
# - Scapin preserves: type, aliases, relation, importance, projects, etc.

merged = existing_frontmatter.copy()
merged.update(apple_metadata)  # Apple fields only
```

### 7.2 Champs Protégés

Ces champs ne sont JAMAIS écrasés par Apple Notes :

```python
PROTECTED_FIELDS = [
    "type", "aliases", "importance", "relation", "relationship_strength",
    "organization", "role", "projects", "stakeholders", "contacts",
    "linked_sources", "pending_updates", "notes_personnelles",
    "last_contact", "mention_count", "first_contact",
]
```

---

## 8. Implémentation

### 8.1 Fichiers à Modifier

| Fichier | Modification |
|---------|--------------|
| `src/passepartout/note_manager.py` | Parser frontmatter enrichi |
| `src/integrations/apple/notes_sync.py` | Protéger champs Scapin |
| `src/passepartout/context_engine.py` | Utiliser aliases pour matching |
| `src/sancho/multi_pass_analyzer.py` | Inclure métadonnées dans contexte |
| `templates/ai/v2/extraction.j2` | Afficher contexte enrichi |

### 8.2 Nouveaux Fichiers

| Fichier | Rôle |
|---------|------|
| `src/passepartout/frontmatter_schema.py` | Schéma et validation |
| `src/passepartout/enrichment_workflows.py` | Workflows background |
| `src/jeeves/api/routers/pending_updates.py` | API validation propositions |

### 8.3 Phases d'Implémentation

| Phase | Contenu | Priorité |
|-------|---------|----------|
| **1** | Schéma + validation frontmatter | Haute |
| **2** | Matching par aliases dans ContextEngine | Haute |
| **3** | Protection champs dans Apple Notes sync | Haute |
| **4** | Workflow Contact Tracker (auto-update) | Moyenne |
| **5** | Workflow Signature Parser (propose) | Moyenne |
| **6** | UI validation pending_updates | Moyenne |
| **7** | Autres workflows (Project Linker, etc.) | Basse |

---

## 9. Exemples Complets

### 9.1 Note PERSONNE

```yaml
---
title: Hugues Lagesse
type: personne
aliases: [Hugues, H. Lagesse, "Mr Lagesse"]
importance: haute

created_at: 2024-06-15T10:30:00+00:00
updated_at: 2026-01-17T14:00:00+00:00
source: scapin

relation: partenaire
relationship_strength: forte
introduced_by: "[[Valerie Lincoln]]"

organization: "[[Ocean River Villa]]"
role: Directeur général
sector: immobilier

email: hugues@oceanrivervilla.mu
phone: "+230 5919 2487"
preferred_language: français
communication_style: formel
timezone: Indian/Mauritius

projects: ["[[Projet Immobilier Maurice]]"]
last_contact: 2026-01-15
mention_count: 12
first_contact: 2024-06-15

linked_sources:
  - type: email
    filter: "from:hugues@oceanrivervilla.mu"
    priority: 1

pending_updates: []

tags: [maurice, immobilier, partenaire]
category: work
---

# Hugues Lagesse

Partenaire de Johan et Damien sur le projet immobilier à Maurice.
Directeur général d'Ocean River Villa.

## Contexte de la relation

Introduit par Valerie Lincoln (banquière) en juin 2024.
Responsable des relations avec les autorités locales et du sourcing terrain.

## Derniers échanges

- 2026-01-15 : Email sur les terrains Heritage Villas Valriche
- 2026-01-10 : Call Teams sur le financement
- 2025-12-20 : Réunion à Azuri sur le planning 2026
```

### 9.2 Note PROJET

```yaml
---
title: Projet Immobilier Maurice
type: projet
aliases: [Ocean River Villa, ORV, Maurice Immo, "Projet Maurice"]
importance: haute

created_at: 2024-06-01T00:00:00+00:00
updated_at: 2026-01-17T14:00:00+00:00
source: scapin

status: actif
priority: haute
domain: immobilier

start_date: 2024-06-01
target_date: 2027-12-31

stakeholders:
  - person: "[[Johan Le Bail]]"
    role: investisseur
  - person: "[[Damien Le Bail]]"
    role: investisseur
  - person: "[[Hugues Lagesse]]"
    role: partenaire local
  - person: "[[Valerie Lincoln]]"
    role: banquière

budget_range: ">100k€"
currency: EUR

related_entities: ["[[Ocean River Villa]]", "[[Azuri Ocean & Golf Village]]"]
last_activity: 2026-01-15
activity_count: 45

linked_sources:
  - type: folder
    path: ~/Documents/Projets/Maurice
    priority: 1
  - type: email
    filter: "subject:maurice OR subject:azuri OR from:@oceanrivervilla"
    priority: 1
  - type: whatsapp
    contact: "Projet Maurice"
    priority: 2

pending_updates: []

tags: [maurice, immobilier, investissement]
category: finance
---

# Projet Immobilier Maurice

Projet d'investissement immobilier à l'île Maurice, en partenariat avec Ocean River Villa.

## Objectif

Acquisition d'un terrain et construction d'une villa à Azuri ou Heritage Villas Valriche.

## Contacts

- **Hugues Lagesse** (Ocean River Villa) — Partenaire local, sourcing terrain
- **Valerie Lincoln** (Banque) — Financement
- **Christophe Piquet** (Heritage Villas) — Contact terrain Valriche

## Historique

- 2026-01-15 : Contact Christophe Piquet pour terrains Valriche
- 2024-06-01 : Démarrage du projet avec Hugues
```

---

## 10. Historique des Décisions

| Date | Décision | Justification |
|------|----------|---------------|
| 2026-01-17 | Création de la spec | Améliorer le contexte IA |
| 2026-01-17 | 3 catégories de comportement | Auto-update / Propose / Manual |
| 2026-01-17 | `pending_updates` dans frontmatter | Traçabilité des propositions |
| 2026-01-17 | Champs protégés pour Apple Notes | Préserver le travail Scapin |

---

## 11. Questions Ouvertes

1. **Validation UI** : Comment présenter les `pending_updates` dans l'interface ?
2. **Conflits** : Que faire si Apple Notes modifie un champ protégé ?
3. **Migration** : Comment enrichir les notes existantes (bootstrap) ?
4. **Performance** : Impact des workflows background sur le système ?

---

## Références

- [ARCHITECTURE.md](../../ARCHITECTURE.md) — Note Format Example
- [CROSS_SOURCE_SPEC.md](CROSS_SOURCE_SPEC.md) — linked_sources
- [NOTE_GRANULARITY_SPEC.md](NOTE_GRANULARITY_SPEC.md) — Project-First approach
- [COHERENCE_PASS_SPEC.md](COHERENCE_PASS_SPEC.md) — Validation des enrichissements
