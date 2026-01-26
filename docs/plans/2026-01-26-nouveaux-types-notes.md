# Plan : Ajout de 5 nouveaux types de notes

> Date : 26 janvier 2026
> Types : RESSOURCE, LIEU, PRODUIT, DECISION, OBJECTIF

---

## Objectif

Compléter la taxonomie des notes pour couvrir tous les besoins d'un PKM complet :

| Type | Usage | Exemple |
|------|-------|---------|
| **RESSOURCE** | Contenus consommés (livres, articles, cours) | "Atomic Habits - James Clear" |
| **LIEU** | Endroits physiques | "Restaurant Le Château, Maurice" |
| **PRODUIT** | Outils, équipements, achats | "MacBook Pro M3", "Notion" |
| **DECISION** | Choix importants documentés | "Choix CRM 2026" |
| **OBJECTIF** | Goals 1-5 ans, areas of focus | "Santé optimale", "Liberté financière" |

---

## Fichiers à modifier

| Fichier | Modifications |
|---------|---------------|
| `src/passepartout/note_types.py` | Enum + from_folder + folder_name + ReviewConfig (×5) |
| `src/passepartout/note_enricher.py` | Sections requises (×5) |
| `src/passepartout/frontmatter_schema.py` | 5 dataclasses + AnyFrontmatter |
| `src/passepartout/frontmatter_parser.py` | Imports + détection + parsing (×5) |
| `src/passepartout/retouche_reviewer.py` | TEMPLATE_TYPE_MAP (×5) |
| `tests/unit/test_note_types.py` | Tests pour les 5 types |

---

## Détail par type

### 1. RESSOURCE — Contenus consommés

**Enum et config (note_types.py)**
```python
RESSOURCE = "ressource"  # Livres, articles, cours, podcasts
```

**ReviewConfig**
```python
NoteType.RESSOURCE: ReviewConfig(
    base_interval_hours=168.0,  # 1 semaine - ressources stables
    max_interval_days=180,
    easiness_factor=2.5,
    auto_enrich=True,  # Recherche web utile
    web_search_default=True,  # Enrichir avec infos sur l'auteur/contenu
    skip_revision=False,
),
```

**Sections enrichissement (note_enricher.py)**
```python
NoteType.RESSOURCE: [
    ("Résumé", "Points clés et enseignements"),
    ("Citations", "Passages marquants"),
    ("Applications", "Comment appliquer ces idées"),
    ("Critique", "Points forts et limites"),
    ("Source", "Où trouver cette ressource"),
],
```

**Frontmatter (frontmatter_schema.py)**
```python
@dataclass
class RessourceFrontmatter(BaseFrontmatter):
    """Frontmatter pour une note de type RESSOURCE."""

    type: NoteType = NoteType.RESSOURCE

    # === IDENTIFICATION ===
    resource_type: Optional[str] = None  # livre, article, video, podcast, cours
    author: Optional[str] = None
    publisher: Optional[str] = None
    year: Optional[int] = None

    # === ACCÈS ===
    url: Optional[str] = None
    isbn: Optional[str] = None

    # === CONSOMMATION ===
    status: Optional[str] = None  # à_lire, en_cours, terminé, abandonné
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    rating: Optional[int] = None  # 1-5

    # === CLASSIFICATION ===
    topics: list[str] = field(default_factory=list)
    recommended_by: Optional[str] = None  # Wikilink [[Personne]]
```

**Mapping dossier**
- from_folder: `"ressources"` → `RESSOURCE`
- folder_name: `"Ressources"`

---

### 2. LIEU — Endroits physiques

**Enum et config (note_types.py)**
```python
LIEU = "lieu"  # Restaurants, hôtels, destinations, adresses
```

**ReviewConfig**
```python
NoteType.LIEU: ReviewConfig(
    base_interval_hours=720.0,  # 30 jours - lieux changent peu
    max_interval_days=365,
    easiness_factor=2.5,
    auto_enrich=True,
    web_search_default=True,  # Infos pratiques, horaires, avis
    skip_revision=False,
),
```

**Sections enrichissement (note_enricher.py)**
```python
NoteType.LIEU: [
    ("Localisation", "Adresse et accès"),
    ("Description", "Ce qu'on y trouve"),
    ("Avis", "Expérience personnelle"),
    ("Pratique", "Horaires, prix, contact"),
    ("Recommandations", "Ce qu'il faut essayer"),
],
```

**Frontmatter (frontmatter_schema.py)**
```python
@dataclass
class LieuFrontmatter(BaseFrontmatter):
    """Frontmatter pour une note de type LIEU."""

    type: NoteType = NoteType.LIEU

    # === IDENTIFICATION ===
    lieu_type: Optional[str] = None  # restaurant, hotel, ville, adresse, magasin

    # === LOCALISATION ===
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    gps: Optional[str] = None  # "latitude, longitude"
    maps_url: Optional[str] = None

    # === CONTACT ===
    phone: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None

    # === ÉVALUATION ===
    rating: Optional[int] = None  # 1-5
    price_range: Optional[str] = None  # €, €€, €€€, €€€€
    last_visit: Optional[datetime] = None

    # === CONTEXTE ===
    recommended_by: Optional[str] = None  # Wikilink [[Personne]]
    visited_with: list[str] = field(default_factory=list)  # Wikilinks
```

**Mapping dossier**
- from_folder: `"lieux"` → `LIEU`
- folder_name: `"Lieux"`

---

### 3. PRODUIT — Outils et équipements

**Enum et config (note_types.py)**
```python
PRODUIT = "produit"  # Outils, équipements, logiciels, achats
```

**ReviewConfig**
```python
NoteType.PRODUIT: ReviewConfig(
    base_interval_hours=336.0,  # 2 semaines
    max_interval_days=180,
    easiness_factor=2.5,
    auto_enrich=True,
    web_search_default=True,  # Specs, alternatives, mises à jour
    skip_revision=False,
),
```

**Sections enrichissement (note_enricher.py)**
```python
NoteType.PRODUIT: [
    ("Description", "Ce que c'est et à quoi ça sert"),
    ("Caractéristiques", "Specs et fonctionnalités"),
    ("Avis", "Expérience d'utilisation"),
    ("Alternatives", "Produits comparables"),
    ("Achat", "Où acheter, prix payé"),
],
```

**Frontmatter (frontmatter_schema.py)**
```python
@dataclass
class ProduitFrontmatter(BaseFrontmatter):
    """Frontmatter pour une note de type PRODUIT."""

    type: NoteType = NoteType.PRODUIT

    # === IDENTIFICATION ===
    product_type: Optional[str] = None  # logiciel, materiel, service, equipement
    brand: Optional[str] = None
    model: Optional[str] = None
    version: Optional[str] = None

    # === ACQUISITION ===
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[str] = None
    purchase_location: Optional[str] = None
    warranty_until: Optional[datetime] = None

    # === ÉTAT ===
    status: Optional[str] = None  # actif, stocké, vendu, jeté
    rating: Optional[int] = None  # 1-5

    # === LIENS ===
    website: Optional[str] = None
    documentation: Optional[str] = None
    related_products: list[str] = field(default_factory=list)
```

**Mapping dossier**
- from_folder: `"produits"` → `PRODUIT`
- folder_name: `"Produits"`

---

### 4. DECISION — Choix documentés

**Enum et config (note_types.py)**
```python
DECISION = "decision"  # Choix importants avec contexte
```

**ReviewConfig**
```python
NoteType.DECISION: ReviewConfig(
    base_interval_hours=720.0,  # 30 jours - décisions à revoir périodiquement
    max_interval_days=365,
    easiness_factor=2.5,
    auto_enrich=False,  # Décisions sont personnelles
    web_search_default=False,
    skip_revision=False,
),
```

**Sections enrichissement (note_enricher.py)**
```python
NoteType.DECISION: [
    ("Contexte", "Situation qui a mené à cette décision"),
    ("Options", "Alternatives considérées"),
    ("Décision", "Le choix fait et pourquoi"),
    ("Conséquences", "Résultats observés"),
],
```

**Frontmatter (frontmatter_schema.py)**
```python
@dataclass
class DecisionFrontmatter(BaseFrontmatter):
    """Frontmatter pour une note de type DECISION."""

    type: NoteType = NoteType.DECISION

    # === DÉCISION ===
    decision_date: Optional[datetime] = None
    decision_maker: Optional[str] = None  # Wikilink ou "moi"
    domain: Optional[str] = None  # tech, finance, carrière, perso

    # === CARACTÉRISTIQUES ===
    reversible: Optional[bool] = None
    impact: Optional[str] = None  # faible, moyen, fort
    confidence: Optional[str] = None  # faible, moyenne, haute

    # === RÉSULTAT ===
    outcome: Optional[str] = None  # positif, négatif, neutre, en_cours
    reviewed_at: Optional[datetime] = None

    # === LIENS ===
    related_project: Optional[str] = None  # Wikilink [[Projet]]
    stakeholders: list[str] = field(default_factory=list)  # Wikilinks
```

**Mapping dossier**
- from_folder: `"decisions"` → `DECISION`, `"décisions"` → `DECISION`
- folder_name: `"Décisions"`

---

### 5. OBJECTIF — Goals et areas of focus

**Enum et config (note_types.py)**
```python
OBJECTIF = "objectif"  # Goals 1-5 ans, areas of focus
```

**ReviewConfig**
```python
NoteType.OBJECTIF: ReviewConfig(
    base_interval_hours=168.0,  # 1 semaine - objectifs à revoir régulièrement
    max_interval_days=30,  # Max 1 mois entre révisions
    easiness_factor=2.0,  # Plus exigeant
    auto_enrich=False,  # Objectifs sont personnels
    web_search_default=False,
    skip_revision=False,
),
```

**Sections enrichissement (note_enricher.py)**
```python
NoteType.OBJECTIF: [
    ("Définition", "Qu'est-ce que cet objectif signifie"),
    ("Pourquoi", "Motivation profonde"),
    ("Indicateurs", "Comment mesurer le progrès"),
    ("Projets", "Initiatives qui contribuent"),
    ("Revue", "État actuel et prochaines étapes"),
],
```

**Frontmatter (frontmatter_schema.py)**
```python
@dataclass
class ObjectifFrontmatter(BaseFrontmatter):
    """Frontmatter pour une note de type OBJECTIF."""

    type: NoteType = NoteType.OBJECTIF

    # === CLASSIFICATION ===
    horizon: Optional[str] = None  # 1_an, 3_ans, 5_ans, area_of_focus
    domain: Optional[str] = None  # santé, finance, carrière, relations, perso

    # === TEMPORALITÉ ===
    target_date: Optional[datetime] = None
    started_at: Optional[datetime] = None

    # === ÉTAT ===
    status: Optional[str] = None  # actif, atteint, abandonné, en_pause
    progress: Optional[int] = None  # 0-100

    # === MESURE ===
    kpis: list[str] = field(default_factory=list)  # Indicateurs clés
    current_value: Optional[str] = None
    target_value: Optional[str] = None

    # === LIENS ===
    parent_objective: Optional[str] = None  # Wikilink [[Objectif parent]]
    contributing_projects: list[str] = field(default_factory=list)  # Wikilinks
```

**Mapping dossier**
- from_folder: `"objectifs"` → `OBJECTIF`
- folder_name: `"Objectifs"`

---

## Ordre dans l'enum NoteType

Pour maintenir un ordre logique (alphabétique par valeur) :

```python
class NoteType(str, Enum):
    CONCEPT = "concept"
    DECISION = "decision"
    ENTITE = "entite"
    EVENEMENT = "evenement"
    LIEU = "lieu"
    OBJECTIF = "objectif"
    PERSONNE = "personne"
    PROCESSUS = "processus"
    PRODUIT = "produit"
    PROJET = "projet"
    RESSOURCE = "ressource"
    REUNION = "reunion"
    SOUVENIR = "souvenir"
    AUTRE = "autre"
```

---

## Commits atomiques

| # | Message | Fichiers |
|---|---------|----------|
| 1 | `feat(notes): ajouter type RESSOURCE` | Tous les fichiers concernés |
| 2 | `feat(notes): ajouter type LIEU` | Tous les fichiers concernés |
| 3 | `feat(notes): ajouter type PRODUIT` | Tous les fichiers concernés |
| 4 | `feat(notes): ajouter type DECISION` | Tous les fichiers concernés |
| 5 | `feat(notes): ajouter type OBJECTIF` | Tous les fichiers concernés |

Alternative : un seul commit groupé si les 5 types sont liés conceptuellement.

---

## Dossiers à créer dans PKM

```
Personal Knowledge Management/
├── Concepts/        ✓ (créé)
├── Décisions/       (à créer)
├── Entités/         ✓
├── Événements/      ✓
├── Lieux/           (à créer)
├── Objectifs/       (à créer)
├── Personnes/       ✓
├── Processus/       ✓
├── Produits/        (à créer)
├── Projets/         ✓
├── Ressources/      (à créer)
├── Réunions/        ✓
├── Souvenirs/       ✓
└── Modèles/         ✓
```

---

## Modèles à créer

5 fichiers dans `PKM/Modèles/` :
- `Modèle — Fiche Ressource.md`
- `Modèle — Fiche Lieu.md`
- `Modèle — Fiche Produit.md`
- `Modèle — Fiche Décision.md`
- `Modèle — Fiche Objectif.md`

---

## Tests à ajouter

Pour chaque type :
1. Présence dans l'enum
2. Mapping from_folder
3. Property folder_name
4. ReviewConfig présente et cohérente

---

## Points d'attention

1. **Pas de migration DB** — NoteType est un string enum

2. **Frontend compatible** — `note_type: string` est générique

3. **OBJECTIF et OmniFocus** — Prévoir une intégration future pour lier objectifs et projets OmniFocus

4. **RESSOURCE et recherche web** — Activer par défaut pour enrichir avec infos auteur/contenu

5. **DECISION et traçabilité** — Les décisions sont sensibles, pas d'enrichissement auto

---

## Estimation

- Code : ~1h (5 types × 10-15 min)
- Modèles : ~30 min (5 fichiers)
- Tests : ~20 min
- Total : ~2h

---

## Validation

```bash
# Tests unitaires
.venv/bin/pytest tests/unit/test_note_types.py -v

# Ruff
.venv/bin/ruff check src/passepartout/

# TypeScript
cd web && npm run check
```
