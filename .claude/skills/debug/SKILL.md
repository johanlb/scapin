---
name: debug
description: Guide de debugging Scapin - Commandes de diagnostic, lecture des logs, erreurs communes et solutions. Utiliser quand quelque chose ne fonctionne pas ou pour investiguer un problème.
allowed-tools: Bash, Read, Grep, Glob
---

# Guide de Debugging Scapin

Référence complète pour diagnostiquer et résoudre les problèmes.

## Quick Diagnostic

**Première étape — toujours commencer par :**

```bash
# 1. Vérifier la santé globale
pkm health

# 2. Voir les erreurs récentes
python scripts/view_errors.py --stats

# 3. Logs en temps réel
pkm --verbose --log-format json process --limit 1
```

---

## Commandes de Diagnostic

### Health Check Complet

```bash
pkm health
```

**Vérifie :**
| Check | Seuils |
|-------|--------|
| Filesystem | Lecture/écriture, permissions |
| Git | État repo, changements non commités |
| Config | Validation fichiers config |
| Dependencies | Packages Python requis |
| IMAP | Connexion serveurs email |
| AI API | Connectivité Anthropic |
| Disk Space | Warning 85%, Critical 95% |
| Queue | Warning 100 items, Critical 1000 |

### Erreurs Accumulées

```bash
# 20 dernières erreurs
python scripts/view_errors.py

# Statistiques globales
python scripts/view_errors.py --stats

# Erreurs non résolues
python scripts/view_errors.py --unresolved

# Par catégorie (IMAP, AI, DATABASE, etc.)
python scripts/view_errors.py --category IMAP

# Par sévérité (LOW, MEDIUM, HIGH, CRITICAL)
python scripts/view_errors.py --severity HIGH

# Détail complet avec traceback
python scripts/view_errors.py --detail ERROR_ID --traceback
```

### État de la Queue

```bash
pkm queue                # Status
pkm stats                # Statistiques globales
pkm stats --detailed     # Breakdown détaillé
```

### Configuration

```bash
pkm config               # Config actuelle
pkm config --validate    # Valider la config
```

---

## Lecture des Logs

### Format des Logs JSON

```json
{
  "timestamp": "2026-01-24T14:30:00.000Z",
  "level": "ERROR",
  "logger": "scapin.sancho",
  "message": "Analysis failed",
  "extra": {
    "email_id": "abc123",
    "pass_number": 2,
    "error": "Rate limit exceeded"
  },
  "source": {
    "file": "multi_pass_analyzer.py",
    "function": "analyze",
    "line": 234
  }
}
```

### Commandes de Consultation

```bash
# Logs du jour
cat data/logs/processing_$(date +%Y-%m-%d).json | jq .

# Filtrer les erreurs
grep -E '"level":\s*"(ERROR|WARNING)"' data/logs/processing_*.json

# Erreurs d'un module spécifique
grep '"logger":\s*"scapin.sancho"' data/logs/*.json | grep ERROR

# Logs en temps réel pendant traitement
pkm --verbose --log-format json process
```

### Fichiers de Logs

| Fichier | Contenu |
|---------|---------|
| `data/logs/processing_YYYY-MM-DD.json` | Traitement emails |
| `data/logs/calendar_YYYY-MM-DD.json` | Événements calendrier |
| `data/logs/teams_YYYY-MM-DD.json` | Messages Teams |
| `data/errors.db` | Erreurs persistées (SQLite) |

---

## Erreurs Communes et Solutions

### 1. IMAP Connection Failed

**Symptôme :** `IMAPError: Connection refused` ou `Authentication failed`

**Diagnostic :**
```bash
python scripts/debug_imap.py
```

**Solutions :**
- Vérifier les credentials dans Keychain : `pkm secrets --list`
- Vérifier la connexion réseau
- Vérifier que le compte IMAP est activé côté serveur
- Pour Gmail : activer "App passwords" ou "Less secure apps"

### 2. AI Rate Limit

**Symptôme :** `RateLimitError` ou `429 Too Many Requests`

**Diagnostic :**
```bash
python scripts/view_errors.py --category AI
```

**Solutions :**
- Attendre quelques minutes (rate limit automatique)
- Réduire `--limit` lors du processing
- Vérifier les quotas sur console.anthropic.com

### 3. Database Locked

**Symptôme :** `DatabaseError: database is locked`

**Diagnostic :**
```bash
ls -la data/scapin.db*
lsof data/scapin.db
```

**Solutions :**
- Fermer les autres processus Scapin
- Supprimer les fichiers `.db-journal` si présents
- Redémarrer le serveur API

### 4. FAISS Index Corrupted

**Symptôme :** Recherche sémantique ne fonctionne plus

**Diagnostic :**
```bash
ls -la data/faiss/
python -c "import faiss; idx = faiss.read_index('data/faiss/notes.index'); print(f'Vectors: {idx.ntotal}')"
```

**Solutions :**
- Reconstruire l'index : endpoint `/api/notes/reindex`
- Supprimer et recréer : `rm -rf data/faiss/ && pkm serve`

### 5. Notes Sync Failed

**Symptôme :** Notes Apple non synchronisées

**Diagnostic :**
```bash
pkm --verbose notes review --all
grep "apple_notes" data/logs/processing_*.json | tail -20
```

**Solutions :**
- Vérifier les permissions macOS pour Notes
- Redémarrer l'app Notes
- Vérifier que le compte iCloud est connecté

### 6. Queue Stuck

**Symptôme :** Items en queue ne sont pas traités

**Diagnostic :**
```bash
pkm queue
pkm stats --detailed
python scripts/view_errors.py --unresolved
```

**Solutions :**
- Vérifier les erreurs bloquantes : `--category VALIDATION`
- Clear et reprocess : `pkm queue --clear` (avec précaution)
- Traiter manuellement : `pkm review`

### 7. Frontend Cannot Connect to API

**Symptôme :** UI affiche "Cannot connect to server"

**Diagnostic :**
```bash
curl http://localhost:8000/api/health
lsof -i :8000
```

**Solutions :**
- Démarrer le serveur : `pkm serve`
- Vérifier le port : `pkm serve --port 8080`
- Tuer les processus zombies : `./scripts/stop.sh`

---

## Scripts de Debug

| Script | Usage |
|--------|-------|
| `scripts/view_errors.py` | Consulter les erreurs accumulées |
| `scripts/debug_imap.py` | Test connectivité IMAP |
| `scripts/fix_corrupted_titles.py` | Réparer titres notes corrompus |
| `scripts/migrate_queue_v24.py` | Migration queue |

---

## Mode Debug Avancé

### Logging Temporaire DEBUG

```python
from src.monitoring.logger import TemporaryLogLevel

with TemporaryLogLevel("DEBUG"):
    # Tout est loggé en DEBUG ici
    process_email(email)
# Retour au niveau normal
```

### Activer Display Mode (masquer logs console)

```python
from src.monitoring.logger import ScapinLogger

ScapinLogger.set_display_mode(True)   # Masquer
# ... UI propre ...
ScapinLogger.set_display_mode(False)  # Restaurer
```

### API Health Check Détaillé

```bash
curl -s http://localhost:8000/api/health | jq .
curl -s http://localhost:8000/api/stats | jq .
curl -s http://localhost:8000/api/status | jq .
```

---

## Catégories d'Erreurs

| Catégorie | Description | Stratégie |
|-----------|-------------|-----------|
| `IMAP` | Connexion email | RECONNECT |
| `AI` | API Claude | RETRY |
| `VALIDATION` | Données invalides | SKIP |
| `FILESYSTEM` | Fichiers/permissions | MANUAL |
| `DATABASE` | SQLite/FAISS | RECONNECT |
| `NETWORK` | Réseau général | RETRY |
| `CONFIGURATION` | Config invalide | MANUAL |
| `PARSING` | Parse de données | SKIP |

---

## Exceptions Scapin

```python
from src.core.exceptions import (
    ScapinError,          # Base - catch all Scapin errors
    EmailProcessingError,
    AIAnalysisError,
    ValidationError,
    RateLimitError,
    AuthenticationError,
    ConfigurationError,
    DatabaseError,
    IMAPError,
    NetworkError,
)

try:
    # operations
except ScapinError as e:
    logger.error(f"Scapin error: {e}", exc_info=True)
```

---

## Checklist Debug Rapide

```
□ pkm health — tous les checks passent ?
□ python scripts/view_errors.py --stats — erreurs récentes ?
□ pkm --verbose process --limit 1 — logs visibles ?
□ curl localhost:8000/api/health — API répond ?
□ ls -la data/ — fichiers présents et permissions OK ?
□ Logs du jour — grep ERROR data/logs/processing_*.json
```
