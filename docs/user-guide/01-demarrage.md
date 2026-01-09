# 1. Démarrage Rapide

## Installation

### Prérequis

- Python 3.11+
- Node.js 20+
- Compte email (Gmail, iCloud, Outlook)
- Clé API Anthropic (Claude)

### Installation Backend

```bash
# Cloner le dépôt
git clone https://github.com/johanlb/scapin.git
cd scapin

# Créer l'environnement virtuel
python -m venv .venv
source .venv/bin/activate

# Installer les dépendances
pip install -e .
```

### Installation Frontend

```bash
cd web
npm install
```

### Configuration

Créer un fichier `.env` à la racine :

```bash
# Email (exemple Gmail)
EMAIL_ADDRESS=votre-email@gmail.com
EMAIL_PASSWORD=mot-de-passe-application
IMAP_SERVER=imap.gmail.com
SMTP_SERVER=smtp.gmail.com

# IA
ANTHROPIC_API_KEY=sk-ant-...

# Authentification
AUTH__ENABLED=true
AUTH__JWT_SECRET_KEY=votre-secret-32-caracteres-min
AUTH__PIN_HASH=$2b$12$...  # Hash bcrypt de votre PIN

# Stockage
STORAGE_DIR=./data
```

> **Note** : Pour Gmail, utilisez un [mot de passe d'application](https://support.google.com/accounts/answer/185833).

---

## Démarrage

### Démarrer le Backend

```bash
source .venv/bin/activate
scapin serve --reload
```

Le serveur démarre sur `http://localhost:8000`.

### Démarrer le Frontend

```bash
cd web
npm run dev
```

L'interface est accessible sur `http://localhost:5173`.

---

## Première Connexion

### 1. Accéder à l'Application

Ouvrez `http://localhost:5173` dans votre navigateur.

### 2. Saisir le PIN

Entrez votre code PIN (4-6 chiffres) sur le clavier numérique.

### 3. Dashboard

Après connexion, vous arrivez sur le **Briefing** — votre tableau de bord quotidien.

---

## Interface Principale

### Layout Desktop

```
┌─────────────────────────────────────────────────────────┐
│  [Sidebar]     │     [Contenu Principal]    │  [Chat]   │
│                │                            │           │
│  - Briefing    │     Votre page active      │  Scapin   │
│  - Flux        │                            │  Assistant│
│  - Notes       │                            │           │
│  - Journal     │                            │           │
│  - Stats       │                            │           │
│  - Settings    │                            │           │
└─────────────────────────────────────────────────────────┘
```

### Layout Mobile

- **Bottom Nav** : Navigation principale
- **Swipe** : Actions rapides sur les cartes
- **Pull-to-refresh** : Actualiser les données

---

## PWA (Application Mobile)

### Installation iOS

1. Ouvrir Safari sur `http://votre-serveur:5173`
2. Appuyer sur le bouton Partage
3. Sélectionner "Sur l'écran d'accueil"
4. Confirmer "Ajouter"

### Installation Android

1. Ouvrir Chrome sur l'URL
2. Appuyer sur le menu (⋮)
3. Sélectionner "Installer l'application"

---

## Prochaines Étapes

- [Briefing](02-briefing.md) — Comprendre votre tableau de bord
- [Flux](03-flux.md) — Traiter vos emails
- [Notes](04-notes.md) — Organiser vos connaissances
