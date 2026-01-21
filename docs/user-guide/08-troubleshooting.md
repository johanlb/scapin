# 8. Dépannage et Diagnostic

Cette section explique comment diagnostiquer et résoudre les problèmes dans Scapin.

---

## Système de Gestion des Erreurs

Scapin dispose d'un système complet de persistance des erreurs qui stocke toutes les exceptions dans une base SQLite (`errors.db`). Cela permet :

- **Suivi historique** des erreurs
- **Analyse de patterns** récurrents
- **Tracking des tentatives de recovery**
- **Résolution documentée**

### Structure d'une Erreur

Chaque erreur enregistrée contient :

| Champ | Description |
|-------|-------------|
| `id` | Identifiant unique |
| `timestamp` | Date/heure de l'erreur |
| `category` | Catégorie (API, DATABASE, AI, EMAIL, etc.) |
| `severity` | Sévérité (CRITICAL, HIGH, MEDIUM, LOW) |
| `component` | Composant source (ex: `sancho.router`) |
| `operation` | Opération en cours |
| `exception_type` | Type d'exception Python |
| `exception_message` | Message d'erreur |
| `traceback` | Stack trace complet |
| `context` | Données contextuelles (JSON) |
| `recovery_strategy` | Stratégie de récupération utilisée |
| `recovery_attempted` | Si une récupération a été tentée |
| `recovery_successful` | Si la récupération a réussi |
| `resolved` | Si l'erreur est résolue |

---

## Script de Consultation : `view_errors.py`

Le script `scripts/view_errors.py` permet de consulter les erreurs accumulées.

### Installation

Aucune installation requise. Le script utilise les dépendances existantes de Scapin.

### Usage de Base

```bash
# Afficher les 20 dernières erreurs
python scripts/view_errors.py

# Afficher les statistiques globales
python scripts/view_errors.py --stats

# Afficher plus d'erreurs
python scripts/view_errors.py --limit 50
```

### Filtrage

```bash
# Erreurs non résolues uniquement
python scripts/view_errors.py --unresolved

# Erreurs résolues uniquement
python scripts/view_errors.py --resolved

# Filtrer par catégorie
python scripts/view_errors.py --category API
python scripts/view_errors.py --category DATABASE
python scripts/view_errors.py --category AI
python scripts/view_errors.py --category EMAIL

# Filtrer par sévérité
python scripts/view_errors.py --severity CRITICAL
python scripts/view_errors.py --severity HIGH
python scripts/view_errors.py --severity MEDIUM
python scripts/view_errors.py --severity LOW

# Combiner les filtres
python scripts/view_errors.py --unresolved --severity HIGH --limit 10
```

### Détail d'une Erreur

```bash
# Voir le détail complet d'une erreur par son ID
python scripts/view_errors.py --detail abc123def456

# ID partiel accepté (début de l'ID)
python scripts/view_errors.py --detail abc123
```

### Affichage des Tracebacks

```bash
# Inclure les tracebacks dans le résumé
python scripts/view_errors.py --traceback

# Combiner avec filtres
python scripts/view_errors.py --unresolved --traceback
```

### Base de Données Personnalisée

```bash
# Spécifier un chemin vers errors.db
python scripts/view_errors.py --db-path /chemin/vers/errors.db
```

### Exemples de Sortie

#### Résumé des erreurs

```
📋 5 dernières erreurs (non résolues):
------------------------------------------------------------

[HIGH] ConnectionError
  ID: a1b2c3d4... | il y a 5 min | ✗ API
  Component: sancho.router → analyze_email
  Message: Failed to connect to Claude API: timeout after 30s

[MEDIUM] ValidationError
  ID: e5f6g7h8... | il y a 2h | ✗ DATABASE
  Component: passepartout.note_manager → save_note
  Message: Invalid frontmatter: missing required field 'title'
```

#### Statistiques

```
==================================================
📊 STATISTIQUES DES ERREURS
==================================================

📈 Vue d'ensemble:
  Total erreurs:     142
  Résolues:          128
  Non résolues:      14

🔄 Recovery:
  Tentées:           45
  Réussies:          38

📂 Par catégorie:
  API: 52
  DATABASE: 34
  AI: 28
  EMAIL: 18
  OTHER: 10

⚠️  Par sévérité:
  CRITICAL: 3
  HIGH: 21
  MEDIUM: 67
  LOW: 51
```

---

## Catégories d'Erreurs

| Catégorie | Description | Composants typiques |
|-----------|-------------|---------------------|
| `API` | Erreurs d'API externes | Claude API, Microsoft Graph |
| `DATABASE` | Erreurs SQLite/stockage | Metadata store, Queue storage |
| `AI` | Erreurs de traitement IA | Sancho, Multi-pass analyzer |
| `EMAIL` | Erreurs IMAP/email | IMAP client, Email processor |
| `CALENDAR` | Erreurs calendrier | CalDAV, Calendar sync |
| `NOTES` | Erreurs gestion notes | Note manager, Git versioning |
| `NETWORK` | Erreurs réseau | Timeouts, DNS, SSL |
| `CONFIG` | Erreurs configuration | Config loading, Validation |
| `OTHER` | Autres erreurs | Non catégorisées |

---

## Sévérités

| Sévérité | Description | Action requise |
|----------|-------------|----------------|
| `CRITICAL` | Système non fonctionnel | Intervention immédiate |
| `HIGH` | Fonctionnalité majeure impactée | Résolution rapide |
| `MEDIUM` | Fonctionnalité mineure impactée | Résolution planifiée |
| `LOW` | Impact minimal | Résolution optionnelle |

---

## Stratégies de Recovery

Scapin tente automatiquement de récupérer de certaines erreurs :

| Stratégie | Description |
|-----------|-------------|
| `RETRY` | Réessayer l'opération (avec backoff) |
| `FALLBACK` | Utiliser une alternative |
| `SKIP` | Ignorer et continuer |
| `QUEUE` | Mettre en file d'attente pour plus tard |
| `MANUAL` | Intervention manuelle requise |

---

## Résolution des Problèmes Courants

### Erreurs API Claude (AI/API)

**Symptômes** : Timeouts, rate limits, erreurs 5xx

**Solutions** :
1. Vérifier la clé API dans `.env`
2. Vérifier les quotas sur console.anthropic.com
3. Augmenter les timeouts dans la config

### Erreurs IMAP (EMAIL)

**Symptômes** : Connexion refusée, authentification échouée

**Solutions** :
1. Vérifier les credentials IMAP
2. Activer "App Passwords" si 2FA
3. Vérifier les paramètres de serveur

### Erreurs SQLite (DATABASE)

**Symptômes** : Database locked, corruption

**Solutions** :
1. S'assurer qu'une seule instance tourne
2. Vérifier les permissions du fichier
3. Restaurer depuis backup si corrompu

---

## Logs en Temps Réel

Pour voir les logs en temps réel pendant l'exécution :

```bash
# Lancer avec logs verbeux
LOG_LEVEL=DEBUG python -m src.frontin.cli

# Ou via l'API
LOG_LEVEL=DEBUG uvicorn src.frontin.api.app:app --reload
```

---

## Activer les Logs Fichier

Par défaut, les logs vont uniquement sur la console. Pour activer la persistance fichier, modifiez la configuration du logger :

```python
# Dans src/monitoring/logger.py ou au démarrage de l'app
from src.monitoring.logger import ScapinLogger, LogLevel, LogFormat
from pathlib import Path

ScapinLogger.configure(
    level=LogLevel.INFO,
    format=LogFormat.JSON,
    log_file=Path("data/scapin.log")  # Active les logs fichier
)
```

---

## Contact Support

Si les problèmes persistent :

1. Exporter les erreurs récentes : `python scripts/view_errors.py --limit 100 > errors.txt`
2. Vérifier les logs récents
3. Ouvrir une issue sur [GitHub](https://github.com/johanlb/scapin/issues)
