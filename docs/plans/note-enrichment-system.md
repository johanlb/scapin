# Note Enrichment & Review System

**Version**: 1.0
**Date**: 5 janvier 2026
**Priorité**: Absolue

---

## 1. Vue d'Ensemble

### Mission

Transformer les notes d'un stockage passif en une **mémoire vivante** qui s'enrichit et se maintient automatiquement via un système de révision espacée inspiré de l'algorithme SM-2 de SuperMemo.

### Principes Directeurs

1. **Conservatisme** : Ne jamais supprimer sans certitude absolue
2. **Non-blocage** : Le frontend ne doit jamais être ralenti
3. **Transparence** : Toute modification est traçable (Git)
4. **Apprentissage** : Les intervalles s'adaptent au comportement réel

---

## 2. Types de Notes

### Catégories Définies

| Type | Dossier | Description | Révision |
|------|---------|-------------|----------|
| **Entités** | `/Entités/` | Organisations, entreprises, concepts | Modérée |
| **Événements** | `/Événements/` | Événements ponctuels importants | Rare après |
| **Personnes** | `/Personnes/` | Fiches contacts enrichies | Fréquente |
| **Processus** | `/Processus/` | Procédures, workflows | Sur changement |
| **Projets** | `/Projets/` | Projets actifs ou archivés | Très fréquente (actif) |
| **Réunions** | `/Réunions/` | Comptes-rendus de réunions | Modérée |
| **Souvenirs** | `/Souvenirs/` | Mémoires personnelles | Jamais modifié |

### Modèles (Templates)

Les modèles sont stockés dans Apple Notes avec le préfixe "Modèle". Ils seront importés et stockés dans :
```
data/templates/
├── personne.md
├── projet.md
├── reunion.md
├── entite.md
├── evenement.md
├── processus.md
└── souvenir.md
```

---

## 3. Architecture

### Vue Globale

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (SvelteKit)                          │
│  - Lecture instantanée depuis cache                                     │
│  - Notifications via WebSocket                                          │
│  - Jamais bloqué par le backend                                         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ WebSocket (push)
                                 ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                            API (FastAPI)                                │
│  - GET /notes/* : lecture depuis cache mémoire                          │
│  - POST /notes/* : écriture + notification worker                       │
│  - GET /api/review/status : état des révisions                          │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ Queue async
                                 ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      BACKGROUND WORKER (processus séparé)               │
│                                                                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│  │  NoteScheduler  │───▶│  NoteReviewer   │───▶│ NoteEnricher    │     │
│  │  (SM-2 timing)  │    │  (analyse)      │    │ (IA + recherche)│     │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘     │
│           │                                            │                │
│           └────────────────────┬───────────────────────┘                │
│                                ↓                                        │
│                    ┌─────────────────────┐                              │
│                    │  NoteMetadataStore  │                              │
│                    │  (SQLite)           │                              │
│                    └─────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────────┘
```

### Composants

#### 1. NoteMetadataStore (`src/passepartout/note_metadata.py`)

Stockage SQLite des métadonnées de révision.

```python
@dataclass
class NoteMetadata:
    note_id: str
    note_type: NoteType  # Enum: personne, projet, etc.

    # Timestamps
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
    next_review: datetime | None

    # SM-2 Algorithm
    easiness_factor: float  # 1.3 - 2.5, défaut 2.5
    repetition_number: int  # Nombre de révisions réussies consécutives
    interval_hours: float   # Intervalle actuel en heures

    # Tracking
    review_count: int
    last_quality: int | None  # 0-5, dernière qualité de révision
    content_hash: str  # SHA256 pour détecter changements externes

    # Configuration
    importance: ImportanceLevel  # critical, high, normal, low, archive
    auto_enrich: bool  # Permission d'enrichir automatiquement
    web_search_enabled: bool  # Permission de recherche web (défaut: False)

    # Historique
    enrichment_history: list[EnrichmentRecord]
```

#### 2. NoteScheduler (`src/passepartout/note_scheduler.py`)

Implémentation SM-2 adaptée.

```python
class NoteScheduler:
    BASE_INTERVAL_HOURS = 2
    SECOND_INTERVAL_HOURS = 12
    MIN_EASINESS = 1.3
    MAX_EASINESS = 2.5

    def calculate_next_review(
        self,
        metadata: NoteMetadata,
        quality: int,  # 0-5
    ) -> tuple[datetime, float, int]:
        """
        Calcule le prochain intervalle selon SM-2

        Returns:
            (next_review_datetime, new_easiness_factor, new_interval_hours)
        """
        # Formule SM-2
        ef = metadata.easiness_factor
        ef_new = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        ef_new = max(self.MIN_EASINESS, min(self.MAX_EASINESS, ef_new))

        if quality < 3:
            # Reset si qualité insuffisante
            interval = self.BASE_INTERVAL_HOURS
            repetition = 0
        else:
            repetition = metadata.repetition_number + 1
            if repetition == 1:
                interval = self.BASE_INTERVAL_HOURS
            elif repetition == 2:
                interval = self.SECOND_INTERVAL_HOURS
            else:
                interval = metadata.interval_hours * ef_new

        next_review = datetime.now(timezone.utc) + timedelta(hours=interval)
        return next_review, ef_new, interval

    def get_notes_due(self, limit: int = 50) -> list[NoteMetadata]:
        """Récupère les notes à réviser maintenant"""
        ...

    def trigger_immediate_review(self, note_id: str) -> None:
        """Force une révision immédiate (changement détecté)"""
        ...
```

#### 3. NoteReviewer (`src/passepartout/note_reviewer.py`)

Analyse et décision de révision.

```python
@dataclass
class ReviewContext:
    """Contexte complet pour la révision"""
    note: Note
    metadata: NoteMetadata
    linked_notes: list[Note]  # Notes liées via [[wikilinks]]
    recent_changes: list[GitCommit]  # Historique Git récent
    related_emails: list[EmailSummary]  # Emails mentionnant les entités

@dataclass
class ReviewAnalysis:
    """Résultat de l'analyse"""
    needs_update: bool
    confidence: float
    suggested_actions: list[ReviewAction]
    reasoning: str

@dataclass
class ReviewAction:
    action_type: ActionType  # add, update, remove, link
    target: str  # Section ou contenu ciblé
    content: str | None  # Nouveau contenu si applicable
    confidence: float
    reasoning: str

class NoteReviewer:
    async def review_note(self, note_id: str) -> ReviewResult:
        """
        Révise une note complète

        1. Charge le contexte (note + liens + historique)
        2. Analyse via Sancho (IA)
        3. Détermine les actions nécessaires
        4. Applique les actions haute-confiance
        5. Queue les actions basse-confiance pour approbation
        """
        context = await self._load_context(note_id)
        analysis = await self._analyze(context)

        applied = []
        pending = []

        for action in analysis.suggested_actions:
            if action.confidence >= 0.9:
                await self._apply_action(context.note, action)
                applied.append(action)
            else:
                pending.append(action)

        # Calcul qualité pour SM-2
        quality = self._calculate_quality(analysis)

        return ReviewResult(
            note_id=note_id,
            quality=quality,
            applied_actions=applied,
            pending_actions=pending,
            analysis=analysis,
        )
```

#### 4. NoteEnricher (`src/passepartout/note_enricher.py`)

Enrichissement via IA et recherche.

```python
class NoteEnricher:
    async def enrich(
        self,
        note: Note,
        context: ReviewContext,
        web_search_allowed: bool = False,
    ) -> list[Enrichment]:
        """
        Génère des enrichissements possibles

        Sources:
        - Analyse du contenu existant
        - Cross-référence avec notes liées
        - Emails/messages récents (si pertinent)
        - Recherche web (si autorisée)
        """
        enrichments = []

        # Analyse IA du contenu
        gaps = await self._identify_gaps(note, context)

        # Cross-référence avec notes liées
        links = await self._find_missing_links(note, context)

        # Informations des emails récents
        if note.metadata.get("type") == "personne":
            updates = await self._extract_from_emails(note, context)
            enrichments.extend(updates)

        # Recherche web si autorisée
        if web_search_allowed:
            web_info = await self._web_research(note, gaps)
            enrichments.extend(web_info)

        return enrichments
```

#### 5. BackgroundWorker (`src/passepartout/background_worker.py`)

Processus séparé pour les révisions.

```python
class BackgroundWorker:
    """
    Worker qui tourne 24/7 en arrière-plan

    Contraintes:
    - Max 50 révisions par jour
    - Max 5 minutes par session de révision
    - Throttling si CPU > 80%
    - Pause si API rate limited
    """

    MAX_DAILY_REVIEWS = 50
    MAX_SESSION_MINUTES = 5
    SLEEP_BETWEEN_REVIEWS = 10  # secondes

    async def run(self):
        """Boucle principale du worker"""
        while True:
            try:
                if self._should_pause():
                    await asyncio.sleep(60)
                    continue

                # Récupérer notes à réviser
                due_notes = self.scheduler.get_notes_due(
                    limit=min(10, self._remaining_today())
                )

                if not due_notes:
                    await asyncio.sleep(300)  # 5 min si rien à faire
                    continue

                # Réviser chaque note
                for metadata in due_notes:
                    if self._session_timeout():
                        break

                    result = await self.reviewer.review_note(metadata.note_id)
                    await self._update_metadata(metadata, result)
                    await self._notify_if_needed(result)

                    await asyncio.sleep(self.SLEEP_BETWEEN_REVIEWS)

            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(60)
```

---

## 4. Critères de Suppression/Conservation

### Conservation (conservateur)

| Critère | Exemple |
|---------|---------|
| **Dates d'entrevue** | "Dernier contact: 15 janvier 2026" |
| **Actions en cours** | "[ ] Envoyer proposition" |
| **Projets/jalons** | "Projet X lancé en mars 2025" |
| **Relations** | "Travaille avec [[Marie]]" |
| **Contexte professionnel** | "Directeur chez ABC Corp" |
| **Souvenirs personnels** | Type "Souvenirs" - jamais modifié |

### Suppression (très prudent)

| Critère | Exemple | Condition |
|---------|---------|-----------|
| **Info obsolète** | "Réunion mardi prochain" | > 1 mois passé |
| **Actions mineures terminées** | "[x] Appeler Jean" | > 2 semaines |
| **Remarques temporelles** | "Cette semaine, faire X" | Contexte passé |
| **Doublons** | Même info dans note liée | Redondance claire |

### Processus de Suppression

```
1. Identification du contenu potentiellement obsolète
2. Vérification qu'il n'a pas de valeur contextuelle
3. Vérification qu'il n'y a pas de référence depuis d'autres notes
4. Si confiance < 0.95 → proposer à l'utilisateur
5. Si confiance >= 0.95 → archiver (pas supprimer) dans section "---Historique---"
```

---

## 5. Fusion Intelligente (Conflits)

### Scénario

Johan modifie une note dans Apple Notes pendant que Scapin la révise.

### Algorithme de Fusion

```python
class NoteMerger:
    async def merge(
        self,
        original: str,      # Version avant révision
        user_version: str,  # Modifications de Johan
        scapin_version: str # Enrichissements de Scapin
    ) -> MergeResult:
        """
        Fusion à 3 voies (three-way merge)

        1. Identifier les changements de chaque côté
        2. Appliquer les changements non-conflictuels
        3. Pour les conflits:
           - Changements de Johan ont priorité sur même section
           - Ajouts de Scapin sont préservés si pas de conflit
        """
        # Diff3 algorithm
        user_changes = self._diff(original, user_version)
        scapin_changes = self._diff(original, scapin_version)

        merged = original
        for change in user_changes:
            merged = self._apply_change(merged, change)

        for change in scapin_changes:
            if not self._conflicts_with(change, user_changes):
                merged = self._apply_change(merged, change)
            else:
                # Johan a priorité - on note l'enrichissement proposé
                self._save_pending_enrichment(change)

        return MergeResult(
            content=merged,
            applied_user_changes=len(user_changes),
            applied_scapin_changes=len([c for c in scapin_changes if not conflicts]),
            pending_enrichments=pending,
        )
```

---

## 6. Intégration Briefing

### Section "Révision des Notes" dans le Briefing Matinal

```markdown
## 📝 Notes Révisées (dernières 24h)

### Enrichissements Appliqués (3)
- **[[Jean Dupont]]** : Ajout nouveau rôle "Directeur Innovation" (source: email)
- **[[Projet Alpha]]** : Mise à jour statut → "En production"
- **[[ABC Corp]]** : Ajout contact secondaire Marie Martin

### Actions en Attente (2)
- **[[Réunion Budget Q1]]** : Proposer suppression (date passée) → [Approuver] [Garder]
- **[[Pierre Martin]]** : Enrichissement suggéré (nouveau projet détecté) → [Voir]

### Prochaines Révisions
- 14 notes prévues aujourd'hui
- Prochaine: [[Projet Beta]] dans 2h
```

---

## 7. Structure des Fichiers

```
src/passepartout/
├── note_manager.py          # Existant - CRUD notes
├── note_metadata.py         # NOUVEAU - Store SQLite métadonnées
├── note_scheduler.py        # NOUVEAU - Planification SM-2
├── note_reviewer.py         # NOUVEAU - Analyse et révision
├── note_enricher.py         # NOUVEAU - Enrichissement IA
├── note_merger.py           # NOUVEAU - Fusion intelligente
├── note_types.py            # NOUVEAU - Types/catégories de notes
├── background_worker.py     # NOUVEAU - Worker async
├── git_versioning.py        # Existant
└── vector_store.py          # Existant

data/
├── notes/                   # Fichiers Markdown (Git)
├── notes_meta.db            # SQLite métadonnées
├── templates/               # Modèles de notes
└── queue/                   # Queue emails (existant)

src/jeeves/api/routers/
└── review.py                # NOUVEAU - API review status
```

---

## 8. Ordre d'Implémentation

| Étape | Module | Dépendances | Priorité |
|-------|--------|-------------|----------|
| 1 | `note_types.py` | - | P0 |
| 2 | `note_metadata.py` | note_types | P0 |
| 3 | `note_scheduler.py` | note_metadata | P0 |
| 4 | `note_reviewer.py` | scheduler, Sancho | P0 |
| 5 | `note_enricher.py` | reviewer | P1 |
| 6 | `note_merger.py` | - | P1 |
| 7 | `background_worker.py` | scheduler, reviewer | P0 |
| 8 | API `review.py` | worker | P1 |
| 9 | Briefing integration | API | P1 |
| 10 | Tests complets | All | P0 |

---

## 9. Métriques de Succès

| Métrique | Cible |
|----------|-------|
| Notes révisées/jour | 20-50 |
| Temps moyen par révision | < 30s |
| Taux d'enrichissement auto-appliqué | > 80% |
| Conflits de fusion | < 5% |
| Satisfaction utilisateur | À mesurer via feedback |

---

## 10. Questions Ouvertes

1. **Import des modèles Apple Notes** : Comment récupérer les modèles ? Export manuel ou via AppleScript ?

2. **Sync Apple Notes** : Priorité de l'implémentation du sync bidirectionnel ?

3. **Notifications** : Au-delà du briefing, veux-tu des notifications push pour les enrichissements importants ?
