# Cycles Mémoire — Specification v1.0

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

L'IA revisite **toutes** les notes périodiquement pour :
- Enrichir le contenu (liens, contexte)
- Corriger les erreurs (liens cassés, typos)
- Détecter les incohérences avec d'autres notes
- Suggérer des fusions de doublons
- Compléter les champs frontmatter manquants

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

## Cycle 2 : Lecture (Humain)

### Objectif

Johan revisite **toutes** les notes périodiquement pour :
- Entretenir sa mémoire sur ses connaissances
- Redécouvrir des informations oubliées
- Valider/corriger les informations
- Renforcer les connexions mentales

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
| 1.0 | 2026-01-20 | Draft initial — Cycles Retouche/Lecture/Filage |
