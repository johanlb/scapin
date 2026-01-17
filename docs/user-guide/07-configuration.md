# 7. Configuration

Ce guide couvre tous les paramètres de configuration de Scapin.

---

## Fichier .env

Le fichier `.env` à la racine contient les secrets et la configuration principale.

### Email

```bash
# Compte principal
EMAIL_ADDRESS=votre-email@gmail.com
EMAIL_PASSWORD=mot-de-passe-application
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Dossiers (optionnel, défauts ci-dessous)
EMAIL_INBOX_FOLDER=INBOX
EMAIL_ARCHIVE_FOLDER=Archive
EMAIL_REFERENCE_FOLDER=Référence
EMAIL_DELETE_FOLDER=Corbeille

# Compte secondaire (optionnel)
EMAIL_ACCOUNTS__1__ADDRESS=autre@outlook.com
EMAIL_ACCOUNTS__1__PASSWORD=...
EMAIL_ACCOUNTS__1__IMAP_SERVER=outlook.office365.com
```

### Intelligence Artificielle

```bash
# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...
AI_MODEL=claude-3-5-haiku-20241022

# Modèle de fallback (optionnel)
AI_FALLBACK_MODEL=claude-3-haiku-20240307

# Tavily pour recherche web (optionnel)
TAVILY_API_KEY=tvly-...
```

### Microsoft 365 (Teams & Calendrier)

```bash
# Azure App Registration
TEAMS__ENABLED=true
TEAMS__ACCOUNT__CLIENT_ID=votre-client-id
TEAMS__ACCOUNT__TENANT_ID=votre-tenant-id

# Calendrier (même credentials)
CALENDAR__ENABLED=true
CALENDAR__POLL_INTERVAL_SECONDS=300
CALENDAR__DAYS_AHEAD=7
CALENDAR__DAYS_BEHIND=1
```

### Authentification

```bash
AUTH__ENABLED=true
AUTH__JWT_SECRET_KEY=votre-secret-32-caracteres-minimum
AUTH__JWT_EXPIRE_MINUTES=10080  # 7 jours
AUTH__PIN_HASH=$2b$12$...  # bcrypt hash du PIN
```

Générer un hash de PIN :
```python
import bcrypt
pin = "1234"
hash = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()
print(hash)
```

### Stockage

```bash
STORAGE_DIR=./data
LOG_FILE=./logs/scapin.log
LOG_LEVEL=INFO
```

---

## Configuration YAML

Le fichier `config/defaults.yaml` contient les paramètres par défaut.

### Traitement

```yaml
processing:
  enable_cognitive_reasoning: true
  enable_context_enrichment: true
  context_top_k: 5
  context_min_relevance: 0.3
  default_limit: 20
```

### Briefing

```yaml
briefing:
  enabled: true
  morning_hours_behind: 12
  morning_hours_ahead: 24
  pre_meeting_minutes_before: 15
  show_confidence: true
```

### API

```yaml
api:
  host: "0.0.0.0"
  port: 8000
  cors_origins:
    - "http://localhost:5173"
    - "http://localhost:4173"
  rate_limit_per_minute: 60
```

---

## Page Settings

Accessible depuis l'interface web (`/settings`).

### Onglets

#### Intégrations

- État de connexion de chaque source
- Bouton de reconnexion
- Dernière synchronisation

#### Notifications

- Activer/désactiver les notifications push
- Types de notifications à recevoir
- Fréquence (immédiate, horaire, résumé)

#### Apparence

- Thème (clair, sombre, système)
- Densité d'affichage
- Animations

#### Raccourcis

- Liste des raccourcis clavier
- Personnalisation (à venir)

#### Compte

- Changer le PIN
- Exporter les données
- Déconnexion

---

## Intégrations

### Gmail

1. Activer l'accès IMAP dans Gmail
2. Créer un mot de passe d'application :
   - Compte Google → Sécurité
   - Connexion à Google → Mots de passe d'application
   - Générer pour "Courrier"
3. Utiliser ce mot de passe dans `.env`

### iCloud Mail

1. Créer un mot de passe d'application :
   - appleid.apple.com → Sécurité
   - Mots de passe d'application → Générer
2. Serveur : `imap.mail.me.com`

### Outlook / Office 365

1. Azure Portal → App Registrations
2. Créer une nouvelle application
3. Ajouter les permissions :
   - `Mail.Read`
   - `Chat.Read`
   - `Calendars.Read`
4. Copier Client ID et Tenant ID

### OmniFocus

```bash
OMNIFOCUS__ENABLED=true
```

Scapin communique via AppleScript (macOS uniquement).

---

## Seuils de Confiance

### Auto-Apply (Workflow v2.2)

```yaml
thresholds:
  auto_apply: 0.85          # Actions appliquées sans révision si > 85%
  escalation: 0.70          # Escalade vers Sonnet si < 70%
  high_confidence: 0.85
  medium_confidence: 0.70
  low_confidence: 0.50
```

### Urgence

```yaml
urgency:
  critical_hours: 2     # < 2h = critique
  high_hours: 8         # < 8h = haute
  medium_hours: 24      # < 24h = moyenne
```

---

## Révision Espacée

```yaml
review:
  initial_interval_hours: 2
  max_interval_days: 365
  max_daily_reviews: 50
  session_duration_minutes: 5
```

### Par Type de Note

| Type | Intervalle Initial |
|------|-------------------|
| Projet | 2 heures |
| Personne | 2 heures |
| Concept | 4 heures |
| Référence | 12 heures |
| Souvenir | Skip (pas de révision) |

---

## Logs

### Niveaux

| Niveau | Usage |
|--------|-------|
| `DEBUG` | Développement, très verbeux |
| `INFO` | Production normale |
| `WARNING` | Problèmes potentiels |
| `ERROR` | Erreurs à corriger |

### Rotation

```yaml
logging:
  max_size_mb: 10
  backup_count: 5
```

---

## Variables d'Environnement Complètes

| Variable | Description | Défaut |
|----------|-------------|--------|
| `EMAIL_ADDRESS` | Email principal | — |
| `EMAIL_PASSWORD` | Mot de passe app | — |
| `IMAP_SERVER` | Serveur IMAP | — |
| `ANTHROPIC_API_KEY` | Clé API Claude | — |
| `AI_MODEL` | Modèle IA | claude-3-5-haiku |
| `AUTH__ENABLED` | Activer auth | true |
| `AUTH__PIN_HASH` | Hash bcrypt PIN | — |
| `STORAGE_DIR` | Dossier données | ./data |
| `LOG_LEVEL` | Niveau de log | INFO |
| `TEAMS__ENABLED` | Activer Teams | false |
| `CALENDAR__ENABLED` | Activer calendrier | false |

---

## Dépannage

### Email ne se connecte pas

1. Vérifier les credentials
2. Vérifier que IMAP est activé
3. Utiliser un mot de passe d'application
4. Tester avec : `openssl s_client -connect imap.gmail.com:993`

### Teams ne s'authentifie pas

1. Vérifier Client ID et Tenant ID
2. Consentement admin requis pour certaines permissions
3. Vérifier les redirect URIs dans Azure

### API retourne 401

1. Token JWT expiré → Se reconnecter
2. PIN incorrect
3. `AUTH__ENABLED=false` en dev

### Notes non indexées

```bash
# Réindexer manuellement
scapin notes reindex
```
