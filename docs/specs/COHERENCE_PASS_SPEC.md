# Coherence Service — Validation et Maintenance des Notes

**Status**: DRAFT
**Date**: 2026-01-15
**Auteur**: Johan + Claude

---

## Résumé

Le **CoherenceService** est un service réutilisable qui assure la cohérence du PKM via trois modes :

| Mode | Usage | Appelé par |
|------|-------|------------|
| **1. Extraction** | Valide les enrichissements avant écriture | MultiPassAnalyzer |
| **2. Maintenance** | Analyse et refactore les notes individuelles | BackgroundWorker (futur) |
| **3. Batch** | Détecte les doublons cross-notes | API / Scheduler (futur) |

### Design réutilisable

Le service est conçu pour être appelé depuis :
- `MultiPassAnalyzer` (traitement email)
- `BackgroundNoteWorker` (maintenance planifiée - futur)
- API REST (vérification manuelle)
- CLI (commande `scapin check-coherence` - futur)

### Problème résolu

| Situation | Sans cohérence | Avec cohérence |
|-----------|----------------|----------------|
| Note "Location - Nautil 6" existe | Crée "Nautil 6 - locataires" | Enrichit "Location - Nautil 6" |
| Info déjà présente dans note | Ajoute un doublon | Détecte et ignore |
| Email parle de "Marc" | Crée note "Marc" | Enrichit "Marc Dupont" (existant) |

---

## Architecture

### Position dans le pipeline

```
Pass 1: Extraction aveugle
    ↓
Pass 2-3: Raffinement contextuel (snippets 500 chars)
    ↓
Pass 4-5: Raisonnement profond (si escalade)
    ↓
┌─────────────────────────────────────────────┐
│  PASS COHERENCE (NOUVEAU)                   │
│  - Charge contenu COMPLET des notes cibles  │
│  - Vérifie cohérence enrichir/créer         │
│  - Identifie section appropriée             │
│  - Détecte doublons                         │
└─────────────────────────────────────────────┘
    ↓
Résultat final validé
```

### Quand s'exécute-t-il ?

- **Toujours** après les passes d'extraction (1-3 ou 1-5)
- **Avant** de retourner le résultat final
- **Condition** : Au moins une extraction avec `note_action` défini

### Modèle utilisé

- **Haiku** par défaut (validation simple)
- **Sonnet** si > 3 notes cibles ou structures complexes

---

## Données d'entrée

### 1. Extractions proposées

```python
extractions: list[Extraction]
# Pour chaque extraction:
# - note_cible: str | None
# - note_action: "enrichir" | "creer"
# - info: str
# - type: str
# - importance: str
```

### 2. Notes cibles (contenu complet)

Pour chaque `note_cible` unique dans les extractions :

```python
@dataclass
class FullNoteContext:
    title: str
    full_content: str          # Contenu COMPLET (pas snippet)
    sections: list[str]        # Headers détectés (## Section)
    entry_count: int           # Nombre d'entrées existantes
    last_entry_date: str       # Date dernière entrée
    note_type: str             # personne, projet, actif, etc.
    file_path: str             # Chemin dans le PKM
```

### 3. Notes similaires (alternatives)

Notes trouvées par EntitySearcher qui pourraient être des alternatives :

```python
@dataclass
class SimilarNote:
    title: str
    match_score: float         # Score de correspondance (0-1)
    match_type: str            # "exact", "fuzzy", "partial"
    sections: list[str]        # Headers de la note
    snippet: str               # Aperçu (200 chars)
```

### 4. Index des notes existantes

Liste des notes du PKM pour référence :

```python
existing_notes: list[str]      # ["Marc Dupont", "Nautil 6", "Projet Alpha", ...]
```

---

## Logique de validation

### Règle 1 : Préférer enrichir

```
SI note_cible correspond à une note existante (exact ou fuzzy > 0.8):
    ALORS note_action = "enrichir"
    ET note_cible = titre exact de la note existante
```

### Règle 2 : Détecter les doublons

```
SI info est déjà présente dans note_cible (similarité > 0.9):
    ALORS marquer extraction comme "duplicate"
    ET suggérer de ne pas l'ajouter
```

### Règle 3 : Identifier la section

```
SI note_cible a des sections (## Headers):
    ALORS suggérer la section appropriée

Mapping par type d'extraction:
- deadline, engagement → ## Actions / ## À faire
- fait, decision → ## Historique / ## Notes
- coordonnees → ## Contact / ## Coordonnées
- montant → ## Finances / ## Budget
- evenement → ## Événements / ## Calendrier
```

### Règle 4 : Résoudre les ambiguïtés de noms

```
SI note_cible = "Marc" ET note "Marc Dupont" existe:
    ALORS note_cible = "Marc Dupont"

SI note_cible = "Nautil 6 - locataires" ET note "Location - Nautil 6" existe:
    ALORS note_cible = "Location - Nautil 6"
```

### Règle 5 : Valider les créations

```
SI note_action = "creer":
    VÉRIFIER qu'aucune note similaire n'existe
    SI note similaire existe (score > 0.7):
        ALORS suggérer "enrichir" à la place
        ET demander confirmation si score < 0.85
```

---

## Format de sortie

```json
{
  "validated_extractions": [
    {
      "original_note_cible": "Nautil 6 - locataires",
      "validated_note_cible": "Location - Nautil 6",
      "note_action": "enrichir",
      "suggested_section": "## Historique location",
      "is_duplicate": false,
      "confidence": 0.95,
      "changes": ["Corrigé cible: 'Nautil 6 - locataires' → 'Location - Nautil 6'"],

      "info": "Nouveau locataire intéressé...",
      "type": "fait",
      "importance": "moyenne"
    }
  ],

  "warnings": [
    {
      "type": "potential_duplicate",
      "extraction_index": 2,
      "message": "Information similaire trouvée dans 'Location - Nautil 6' (entrée du 2024-03-15)"
    },
    {
      "type": "ambiguous_target",
      "extraction_index": 0,
      "message": "Plusieurs notes correspondent à 'Marc': 'Marc Dupont', 'Marc Lefèvre'"
    }
  ],

  "notes_to_create": [
    {
      "suggested_title": "Projet Valriche",
      "reason": "Nouveau projet distinct de 'Projet Immobilier Maurice'",
      "confidence": 0.85
    }
  ],

  "coherence_summary": {
    "total_extractions": 4,
    "validated": 3,
    "corrected": 1,
    "duplicates_detected": 0,
    "creations_validated": 1
  },

  "coherence_confidence": 0.92,

  "reasoning": "Toutes les extractions ont été validées. La cible 'Nautil 6 - locataires' a été corrigée vers la note existante 'Location - Nautil 6'. Aucun doublon détecté."
}
```

---

## Template Jinja2

Voir `templates/ai/v2/pass_coherence.j2`

Structure :
1. Rappel de l'email original (résumé)
2. Extractions proposées à valider
3. Notes cibles avec contenu COMPLET
4. Notes similaires (alternatives)
5. Index des notes existantes
6. Règles de validation
7. Format de sortie attendu

---

## Implémentation

### Fichiers à créer/modifier

| Fichier | Action | Description |
|---------|--------|-------------|
| `templates/ai/v2/pass_coherence.j2` | Créer | Template du prompt |
| `src/sancho/coherence_validator.py` | Créer | Logique de validation |
| `src/sancho/multi_pass_analyzer.py` | Modifier | Intégrer le pass |
| `src/passepartout/note_manager.py` | Modifier | Méthode `get_full_content()` |

### Méthodes à ajouter

```python
# note_manager.py
async def get_full_note_context(self, note_title: str) -> FullNoteContext:
    """Charge le contenu complet d'une note avec ses sections."""

async def detect_sections(self, content: str) -> list[str]:
    """Extrait les headers ## d'une note."""

# coherence_validator.py
class CoherenceValidator:
    async def validate(
        self,
        extractions: list[Extraction],
        event: PerceivedEvent
    ) -> CoherenceResult:
        """Valide les extractions contre les notes existantes."""
```

---

## Exemples

### Exemple 1 : Correction de cible

**Input:**
```
Extraction: "Nouveau locataire intéressé pour Nautil 6"
note_cible: "Nautil 6"
note_action: "enrichir"
```

**Notes existantes:**
- "Nautil 6" (actif principal)
- "Location - Nautil 6" (sous-note location)

**Output:**
```
validated_note_cible: "Location - Nautil 6"
suggested_section: "## Prospection"
changes: ["Redirigé vers note spécifique 'Location - Nautil 6'"]
```

### Exemple 2 : Blocage de création

**Input:**
```
Extraction: "Contact avec Marc pour le projet"
note_cible: "Marc"
note_action: "creer"
```

**Notes existantes:**
- "Marc Dupont" (personne, score 0.92)
- "Marc Lefèvre" (personne, score 0.88)

**Output:**
```
warning: "ambiguous_target"
message: "Plusieurs notes correspondent. Préciser: Marc Dupont ou Marc Lefèvre?"
note_action: "enrichir" (si contexte permet de trancher)
```

### Exemple 3 : Détection de doublon

**Input:**
```
Extraction: "Départ locataires Coette confirmé"
note_cible: "Location - Nautil 6"
```

**Contenu note:**
```markdown
## Historique
- 2021-03-08: Départ locataires Coette confirmé pour le 14/05
```

**Output:**
```
is_duplicate: true
message: "Information déjà présente (entrée du 2021-03-08)"
recommendation: "Ne pas ajouter"
```

---

## Métriques de succès

| Métrique | Cible | Mesure |
|----------|-------|--------|
| Taux de correction | > 20% | Extractions corrigées / Total |
| Doublons évités | > 90% | Doublons détectés / Doublons réels |
| Faux positifs | < 5% | Corrections erronées / Corrections |
| Temps d'exécution | < 3s | Durée moyenne du pass |

---

## Questions ouvertes

1. **Granularité des sections** : Jusqu'à quel niveau de profondeur ? (##, ###, ####)
2. **Seuil de similarité** : 0.9 pour doublons, mais ajustable ?
3. **Création forcée** : Permettre de forcer `creer` même si note similaire existe ?
4. **Historique des corrections** : Logger les corrections pour apprentissage ?

---

## Historique

| Date | Décision |
|------|----------|
| 2026-01-15 | Création de la spec |
