# Cycles Mémoire — Specification v1.1

**Date** : 20 janvier 2026
**Statut** : Draft
**Auteur** : Johan + Claude
**Branche** : `feat/notes-hygiene`

---

## Résumé Exécutif

Scapin maintient les connaissances de Johan via deux cycles indépendants basés sur l'algorithme SM-2 (Spaced Repetition) :

1. **Retouche** (IA) — Amélioration automatique et périodique des notes
2. **Lecture** (Humain) — Entretien de la mémoire humaine via révision espacée

Ces cycles alimentent le **Filage** du matin, qui prépare Johan pour sa journée.

---

## Vocabulaire Théâtral

| Terme | Acteur | Description |
|-------|--------|-------------|
| **Retouche** | IA (Sancho) | Amélioration automatique d'une note (enrichissement, corrections, liens) |
| **Lecture** | Johan | Parcours d'une note pour se la remémorer |
| **Filage** | Scapin | Briefing matinal préparant les Lectures du jour |

---

## Architecture des Cycles

```
┌─────────────────────────────────────────────────────────────────┐
│                           NOTE                                  │
│                                                                 │
│   ┌─────────────────────────┐     ┌─────────────────────────┐   │
│   │   Compteur SM-2         │     │   Compteur SM-2         │   │
│   │   RETOUCHE (IA)         │     │   LECTURE (Humain)      │   │
│   │                         │     │                         │   │
│   │   next_retouche: date   │     │   next_lecture: date    │   │
│   │   retouche_ef: 2.5      │     │   lecture_ef: 2.5       │   │
│   │   retouche_interval: 7d │     │   lecture_interval: 14d │   │
│   │   retouche_count: 5     │     │   lecture_count: 3      │   │
│   └───────────┬─────────────┘     └─────────────┬───────────┘   │
│               │                                 │               │
│               ▼                                 ▼               │
│   ┌─────────────────────────┐     ┌─────────────────────────┐   │
│   │ BYPASS si :             │     │ BYPASS si :             │   │
│   │ • Note modifiée         │     │ • Liée au Filage        │   │
│   │   → Retouche immédiate  │     │   (événements du jour)  │   │
│   └─────────────────────────┘     └─────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Cycle 1 : Retouche (IA)

### Objectif

L'IA revisite **toutes** les notes périodiquement pour maintenir et améliorer la base de connaissances. La Retouche agit comme un **bibliothécaire cognitif** qui prend soin de la mémoire de Johan.

### Les 6 Actions de la Retouche

#### 1. Enrichissement de contenu

L'IA ajoute du contenu, reformule pour plus de clarté :
- Compléter les informations manquantes (depuis le contexte)
- Reformuler les passages confus
- Ajouter des détails pertinents trouvés dans d'autres notes

#### 2. Structuration

L'IA réorganise le contenu pour une meilleure lisibilité :
- Créer/réorganiser les sections et sous-sections
- Établir une hiérarchie logique
- Ajouter des listes à puces pour les énumérations
- Mettre en forme les métadonnées

#### 3. Résumé / Synthèse

L'IA génère un résumé en tête de note :
- Synthèse en 2-3 phrases
- Points clés à retenir
- Contexte rapide pour Johan

#### 4. Scoring Qualité

L'IA évalue la qualité de la note (0-100%) :

| Score | Signification |
|-------|---------------|
| 90-100% | Note complète, bien structurée |
| 70-89% | Bonne note, améliorations mineures possibles |
| 50-69% | Note correcte, enrichissement souhaitable |
| 30-49% | Note incomplète, travail nécessaire |
| 0-29% | Note problématique, attention requise |

Critères d'évaluation :
- Complétude des informations
- Clarté de la structure
- Qualité des liens (wikilinks)
- Fraîcheur des informations
- Absence de contradictions

#### 5. Injection de Questions

L'IA injecte des questions dans la note pour Johan. Ces questions apparaissent lors de la **Lecture** et permettent de compléter la mémoire via un dialogue.

| Type de question | Exemple | Déclencheur |
|------------------|---------|-------------|
| **Clarification** | "Quel est le lien exact entre Marc et Azuri ?" | Relation floue détectée |
| **Information manquante** | "Quelle est la date de cet événement ?" | Champ vide ou imprécis |
| **Validation** | "Cette adresse est-elle toujours valide ?" | Info ancienne (>1 an) |
| **Approfondissement** | "Peux-tu détailler le contexte de cette décision ?" | Note superficielle |
| **Connexion** | "Y a-t-il un lien avec [[Projet X]] ?" | Similarité détectée |

Format dans la note :
```markdown
## Questions en attente
- [ ] Quel est son rôle exact chez Azuri ? (poste, responsabilités)
- [ ] Comment s'est passée la première rencontre ?
- [ ] Y a-t-il un lien avec [[Jennifer Hirst]] ?
```

#### 6. Restructuration du Graphe

La Retouche ne concerne pas seulement la note individuelle, mais maintient la santé de **l'ensemble du graphe de connaissances**.

**Opérations sur le graphe :**

| Opération | Déclencheur | Exemple |
|-----------|-------------|---------|
| **Scinder** | Note > 2000 mots, multi-sujets | "Projet Azuri" → "Azuri - Historique" + "Azuri - Contacts" + "Azuri - Finances" |
| **Fusionner** | Notes très similaires, redondance | "Marc D." + "M. Dupont" + "Marc Dupont (Azuri)" → "Marc Dupont" |
| **Extraire** | Section autonome détectée | Section "Réunion du 15/01" extraite vers note dédiée |
| **Absorber** | Note orpheline, contenu faible | Micro-note absorbée dans note parente |
| **Relier** | Connexion manquante détectée | Ajouter lien [[Jennifer Hirst]] dans "Équipe Azuri" |

**Flux de restructuration :**
```
Retouche de Note X
       │
       ├──▶ Analyse contexte (notes liées + similaires)
       │
       ├──▶ Décisions de restructuration
       │       • Note X : enrichir, restructurer
       │       • Note Y : fusionner dans X
       │       • Note Z : créer (scission de X)
       │
       ├──▶ Exécution (avec seuils de confiance)
       │       • Auto-apply si confiance ≥ 0.9
       │       • Suggestion sinon (validation Johan)
       │
       └──▶ Mise à jour des compteurs SM-2
               • X : retouché
               • Y : archivé (fusionné)
               • Z : nouveau (next_retouche = soon)
```

### Garde-fous

| Risque | Protection |
|--------|------------|
| Perte de données | Snapshot avant restructuration majeure |
| Fusion incorrecte | Confiance ≥ 0.95 pour fusion auto, sinon suggestion |
| Scission excessive | Minimum 500 mots par note créée |
| Chaos des liens | Mise à jour automatique de tous les wikilinks |
| Sur-modification | Max 3 restructurations majeures par jour |

### Exemple de Retouche complète

**Avant Retouche :**
```markdown
# Marc Dupont

Contact chez Azuri. Rencontré en 2021.
Sympa, bon contact.
```

**Après Retouche :**
```markdown
---
title: Marc Dupont
type: personne
organization: "[[Azuri]]"
relation: contact_professionnel
quality_score: 45
last_retouche: 2026-01-20
---

# Marc Dupont

## Résumé
Contact professionnel chez [[Azuri]] depuis 2021. Relation de confiance établie.

## Contexte
Rencontré en 2021 dans le cadre du projet Azuri. Décrit comme sympathique et fiable.

## Contact
- Email : _à compléter_
- Téléphone : _à compléter_
- Poste : _à compléter_

## Questions en attente
- [ ] Quel est son rôle exact chez Azuri ? (poste, responsabilités)
- [ ] Comment s'est passée la première rencontre ?
- [ ] Y a-t-il un lien avec [[Jennifer Hirst]] qui travaille aussi chez Azuri ?

## Historique des interactions
_Aucune interaction documentée_

---
_Qualité : 45% — Enrichissement nécessaire_
```

### Déclencheurs

| Déclencheur | Priorité | Description |
|-------------|----------|-------------|
| **Note modifiée** | Immédiat | Bypass SM-2, retouche dans les 60s |
| **SM-2 due** | Normal | `next_retouche <= now` |
| **Manuel** | À la demande | Bouton 🧹 dans l'UI |

### Algorithme SM-2 pour Retouche

```python
# Après chaque retouche
def update_retouche_sm2(note, quality):
    """
    quality: 0-5
      5 = Note parfaite, rien à améliorer
      4 = Améliorations mineures appliquées
      3 = Améliorations modérées
      2 = Problèmes significatifs corrigés
      1 = Restructuration majeure
      0 = Note problématique, revoir rapidement
    """
    if quality >= 3:
        if note.retouche_count == 0:
            note.retouche_interval = 1  # 1 jour
        elif note.retouche_count == 1:
            note.retouche_interval = 3  # 3 jours
        else:
            note.retouche_interval *= note.retouche_ef

        note.retouche_ef = max(1.3, note.retouche_ef + 0.1 - (5 - quality) * 0.08)
        note.retouche_count += 1
    else:
        # Reset - revoir rapidement
        note.retouche_interval = 1
        note.retouche_count = 0
        note.retouche_ef = max(1.3, note.retouche_ef - 0.2)

    note.next_retouche = now + timedelta(days=note.retouche_interval)
```

### Limites et Throttling

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| `max_retouches_per_day` | 100 | Limite quotidienne |
| `max_retouche_session_minutes` | 10 | Durée max par session |
| `sleep_between_retouches_seconds` | 5 | Pause entre retouches |
| `retouche_quiet_hours` | 23h-7h | Pas de retouches la nuit |

---

## Boucle de Co-construction Retouche ↔ Lecture

La Retouche et la Lecture forment une **boucle de co-construction** où l'IA et Johan collaborent pour enrichir la mémoire :

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   RETOUCHE (IA)                      LECTURE (Johan)            │
│   ─────────────                      ──────────────             │
│                                                                 │
│   • Enrichit le contenu              • Lit la note              │
│   • Restructure                      • Découvre les questions   │
│   • Génère un résumé                 • Répond aux questions     │
│   • Évalue la qualité                • Valide/corrige           │
│   • Injecte des QUESTIONS ──────────────────────┐               │
│         ▲                                       │               │
│         │                                       ▼               │
│         └─────────── Intègre les réponses ──────┘               │
│                                                                 │
│              La mémoire se construit à deux.                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Flux de co-construction :**

1. **Retouche** analyse la note, détecte des lacunes
2. **Retouche** injecte des questions ciblées
3. **Lecture** : Johan lit la note et voit les questions
4. **Lecture** : Johan répond aux questions (texte libre)
5. **Prochaine Retouche** : L'IA intègre les réponses dans le contenu de la note
6. La note s'enrichit progressivement via ce dialogue

---

## Cycle 2 : Lecture (Humain)

### Objectif

Johan revisite **toutes** les notes périodiquement pour :
- Entretenir sa mémoire sur ses connaissances
- Redécouvrir des informations oubliées
- Valider/corriger les informations
- Renforcer les connexions mentales
- **Répondre aux questions de l'IA** pour enrichir la note

### Déroulement d'une Lecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      LECTURE D'UNE NOTE                         │
│                                                                 │
│  1. Affichage de la note                                        │
│     • Résumé en haut                                            │
│     • Score qualité visible                                     │
│     • Contenu complet                                           │
│                                                                 │
│  2. Section "Questions en attente" mise en évidence             │
│     ┌─────────────────────────────────────────────────────────┐ │
│     │ ❓ Questions de Scapin                                  │ │
│     │                                                         │ │
│     │ • Quel est son rôle exact chez Azuri ?                  │ │
│     │   [Répondre] [Je ne sais pas] [Question non pertinente] │ │
│     │                                                         │ │
│     │ • Y a-t-il un lien avec [[Jennifer Hirst]] ?            │ │
│     │   [Répondre] [Je ne sais pas] [Question non pertinente] │ │
│     └─────────────────────────────────────────────────────────┘ │
│                                                                 │
│  3. Validation finale                                           │
│     • "Comment était ce souvenir ?" (échelle 0-5)               │
│     • Mise à jour SM-2                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Déclencheurs

| Déclencheur | Priorité | Description |
|-------------|----------|-------------|
| **Filage du matin** | Contextuel | Notes liées aux événements du jour |
| **SM-2 due** | Normal | `next_lecture <= now` |
| **Post-retouche** | Découverte | Notes fraîchement retouchées par l'IA |

### Algorithme SM-2 pour Lecture

```python
# Après chaque lecture validée par Johan
def update_lecture_sm2(note, quality):
    """
    quality: 0-5
      5 = Je me souviens parfaitement
      4 = Bon souvenir, petits détails oubliés
      3 = Souvenir correct avec effort
      2 = Souvenir difficile
      1 = Souvenir très vague
      0 = Totalement oublié
    """
    # Même algorithme SM-2 standard
    if quality >= 3:
        if note.lecture_count == 0:
            note.lecture_interval = 1  # 1 jour
        elif note.lecture_count == 1:
            note.lecture_interval = 6  # 6 jours
        else:
            note.lecture_interval *= note.lecture_ef

        note.lecture_ef = max(1.3, note.lecture_ef + 0.1 - (5 - quality) * 0.08)
        note.lecture_count += 1
    else:
        # Reset - revoir rapidement
        note.lecture_interval = 1
        note.lecture_count = 0
        note.lecture_ef = max(1.3, note.lecture_ef - 0.2)

    note.next_lecture = now + timedelta(days=note.lecture_interval)
```

### Interaction avec Retouche

Quand l'IA retouche une note :
- Si améliorations significatives (quality <= 3) → Programmer une Lecture rapidement
- Si note parfaite (quality >= 4) → Ne pas affecter le cycle Lecture

---

## Filage du Matin

### Objectif

Préparer Johan pour sa journée avec une sélection de **maximum 20 Lectures** pertinentes.

### Algorithme de Sélection

```python
def prepare_filage(date: date, max_lectures: int = 20) -> list[Note]:
    lectures = []

    # Priorité 1 : Notes liées aux événements du jour
    events = calendar.get_events(date)
    for event in events:
        related_notes = find_notes_related_to_event(event)
        for note in related_notes:
            if note not in lectures:
                lectures.append(note)
                note.filage_reason = "event"
                note.filage_event = event.title

    # Priorité 2 : Notes dues SM-2 (mémoire à entretenir)
    if len(lectures) < max_lectures:
        due_notes = get_lectures_due(date)
        due_notes.sort(key=lambda n: n.next_lecture)  # Plus en retard d'abord
        for note in due_notes:
            if note not in lectures and len(lectures) < max_lectures:
                lectures.append(note)
                note.filage_reason = "due"
                note.filage_overdue_days = (date - note.next_lecture).days

    # Priorité 3 : Notes fraîchement retouchées
    if len(lectures) < max_lectures:
        recent_retouches = get_recently_retouched(hours=48)
        for note in recent_retouches:
            if note not in lectures and len(lectures) < max_lectures:
                lectures.append(note)
                note.filage_reason = "retouched"
                note.filage_retouched_at = note.last_retouche

    return lectures
```

### Présentation du Filage

```
┌─────────────────────────────────────────────────────────────────┐
│                     FILAGE DU JOUR                              │
│                   Lundi 20 janvier 2026                         │
│                      12 Lectures                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📅 LIÉES À TA JOURNÉE (4)                                      │
│  ─────────────────────────────────────────────────────────────  │
│  • Marc Dupont                        → Réunion 10h00           │
│  • Projet Azuri                       → Call 14h00              │
│  • Afrasia Bank                       → Signature 16h00         │
│  • Nautil 12                          → Visite 17h30            │
│                                                                 │
│  🧠 MÉMOIRE À ENTRETENIR (5)                                    │
│  ─────────────────────────────────────────────────────────────  │
│  • Jennifer Hirst                     ⚠️ 3 jours de retard      │
│  • Processus recrutement              ⚠️ 2 jours de retard      │
│  • Architecture Scapin                ⚠️ 1 jour de retard       │
│  • Contrat IBL                        📆 Due aujourd'hui        │
│  • Fiscalité Maurice                  📆 Due aujourd'hui        │
│                                                                 │
│  ✨ FRAÎCHEMENT RETOUCHÉES (3)                                  │
│  ─────────────────────────────────────────────────────────────  │
│  • Famille Crepineau                  🔄 Enrichie hier          │
│  • Azuri Village                      🔄 Liens ajoutés          │
│  • Ocean Edge                         🔄 Structure améliorée    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  [Commencer le Filage]              [Reporter à plus tard]      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Modèle de Données

### Extension NoteMetadata

```python
@dataclass
class NoteMetadata:
    note_id: str
    note_type: NoteType

    # Cycle Retouche (IA)
    next_retouche: Optional[datetime] = None
    retouche_ef: float = 2.5  # Easiness Factor
    retouche_interval: float = 1.0  # Jours
    retouche_count: int = 0
    last_retouche: Optional[datetime] = None
    last_retouche_quality: Optional[int] = None

    # Cycle Lecture (Humain)
    next_lecture: Optional[datetime] = None
    lecture_ef: float = 2.5
    lecture_interval: float = 1.0
    lecture_count: int = 0
    last_lecture: Optional[datetime] = None
    last_lecture_quality: Optional[int] = None

    # Métadonnées existantes...
    created_at: datetime
    updated_at: datetime
    importance: Importance
    # ...
```

### Migration SQLite

```sql
ALTER TABLE note_metadata ADD COLUMN next_retouche TIMESTAMP;
ALTER TABLE note_metadata ADD COLUMN retouche_ef REAL DEFAULT 2.5;
ALTER TABLE note_metadata ADD COLUMN retouche_interval REAL DEFAULT 1.0;
ALTER TABLE note_metadata ADD COLUMN retouche_count INTEGER DEFAULT 0;
ALTER TABLE note_metadata ADD COLUMN last_retouche TIMESTAMP;
ALTER TABLE note_metadata ADD COLUMN last_retouche_quality INTEGER;

ALTER TABLE note_metadata ADD COLUMN next_lecture TIMESTAMP;
ALTER TABLE note_metadata ADD COLUMN lecture_ef REAL DEFAULT 2.5;
ALTER TABLE note_metadata ADD COLUMN lecture_interval REAL DEFAULT 1.0;
ALTER TABLE note_metadata ADD COLUMN lecture_count INTEGER DEFAULT 0;
ALTER TABLE note_metadata ADD COLUMN last_lecture TIMESTAMP;
ALTER TABLE note_metadata ADD COLUMN last_lecture_quality INTEGER;

-- Index pour les requêtes de scheduling
CREATE INDEX idx_next_retouche ON note_metadata(next_retouche);
CREATE INDEX idx_next_lecture ON note_metadata(next_lecture);
```

---

## Background Worker — Nouvelle Architecture

### Boucle Principale

```
┌─────────────────────────────────────────────────────────────────┐
│                    BOUCLE PRINCIPALE                            │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 1. Reset stats quotidiens (minuit)                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 2. Préparer Filage (6h du matin)                           │ │
│  │    → Sélectionner les 20 Lectures du jour                  │ │
│  │    → Notifier Johan                                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 3. Janitor (toutes les 24h)                                │ │
│  │    → Valider/réparer structure des notes                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 4. Ingestion (toutes les 60s)                              │ │
│  │    → Détecter notes modifiées                              │ │
│  │    → Programmer Retouche immédiate si modifiée             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 5. Cycle Retouche (continu, hors heures calmes)            │ │
│  │    → Récupérer notes dues (next_retouche <= now)           │ │
│  │    → Exécuter Retouche IA                                  │ │
│  │    → Mettre à jour compteur SM-2                           │ │
│  │    → Max 100/jour, sessions de 10 min                      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│                     (recommence la boucle)                      │
└─────────────────────────────────────────────────────────────────┘
```

### Configuration

```python
@dataclass
class WorkerConfig:
    # Filage
    filage_hour: int = 6  # Heure de préparation du Filage
    filage_max_lectures: int = 20

    # Janitor
    janitor_interval_hours: float = 24.0

    # Ingestion
    ingestion_interval_seconds: float = 60.0

    # Cycle Retouche
    max_retouches_per_day: int = 100
    max_retouche_session_minutes: int = 10
    sleep_between_retouches_seconds: float = 5.0
    retouche_quiet_start: int = 23  # 23h
    retouche_quiet_end: int = 7     # 7h

    # Général
    sleep_when_idle_seconds: float = 60.0
    sleep_on_error_seconds: float = 60.0
```

---

## API Endpoints

### Filage

```http
GET /api/filage
```

Retourne le Filage du jour (préparé à 6h ou à la demande).

```http
POST /api/filage/lecture/{note_id}/complete
Content-Type: application/json

{
  "quality": 4  // 0-5 : qualité du souvenir
}
```

Marque une Lecture comme terminée et met à jour SM-2.

### Retouche

```http
POST /api/notes/{note_id}/retouche
```

Déclenche une Retouche manuelle (bypass SM-2).

```http
GET /api/notes/{note_id}/cycles
```

Retourne l'état des deux cycles SM-2 pour une note.

---

## Liens avec Autres Specs

| Spec | Relation |
|------|----------|
| `NOTE_HYGIENE_SPEC.md` | La Retouche utilise le même pipeline d'analyse hygiène |
| `USER_SCENARIOS.md` | Le Filage s'intègre au scénario "Matin de Johan" |
| `PERIPETIES_REFONTE_SPEC.md` | Les Retouches peuvent générer des suggestions dans Péripéties |

---

## Changelog

| Version | Date | Changements |
|---------|------|-------------|
| 1.1 | 2026-01-20 | Ajout détails Retouche (6 actions, restructuration graphe, questions), boucle co-construction |
| 1.0 | 2026-01-20 | Draft initial — Cycles Retouche/Lecture/Filage |
