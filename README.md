# 🎭 Scapin — Votre Gardien Cognitif Personnel

**Version** : 1.0.0-alpha  
**Statut** : 🏗️ Développement actif — Architecture cognitive complète  
**Python** : 3.9+

> Nommé d'après Scapin, le valet rusé et inventif de Molière qui trouve toujours une solution.

---

## 🎯 Vision

### La Mission

> **"Prendre soin de vous mieux que vous-même."**

Scapin n'est pas un simple processeur d'emails ou un gestionnaire de tâches. C'est un **gardien cognitif proactif** — une extension active de votre esprit qui anticipe vos besoins, prépare le terrain, et pense le plus loin possible pour vous.

### Ce que Scapin Fait

- **Perçoit** les événements entrants (emails, fichiers, questions, calendrier)
- **Raisonne** avec conscience du contexte et réflexion multi-étapes itérative
- **Décide** intelligemment via des passes cognitives jusqu'à 95% de confiance
- **Apprend** continuellement de vos corrections et des résultats
- **Agit** comme votre valet numérique de confiance — anticipant, préparant, facilitant

### La Tension Centrale Résolue

> **Paradoxe** : Besoin de déléguer massivement (trop de choses à gérer) ET de préserver la capacité à penser (débat, challenge, exploration).

**Résolution** : Scapin est simultanément :
- **Déchargeur cognitif** — Pour les micro-tâches et le contexte factuel
- **Sparring partner intellectuel** — Pour le débat, l'exploration, le challenge des idées

Ces deux rôles libèrent de la bande passante cognitive pour se concentrer sur l'essentiel.

---

## 📚 Philosophie Fondatrice

La conception de Scapin s'appuie sur des fondements théoriques solides :

| Concept | Source | Application |
|---------|--------|-------------|
| **Extended Mind** | Clark & Chalmers (1998) | Scapin est une extension de votre cognition, pas un outil externe |
| **Mémoire Transactive** | Wegner (1985) | Vous + Scapin formez un système de mémoire partagée |
| **Pharmacologie** | Stiegler | Scapin augmente vos capacités au lieu de les remplacer |
| **Effet Google** | Sparrow et al. (2011) | Scapin gère la localisation, vous gardez l'essentiel |

### Les 5 Principes Directeurs

| # | Principe | Description |
|---|----------|-------------|
| **1** | **Qualité sur vitesse** | 10-20 secondes de raisonnement pour la BONNE décision |
| **2** | **Proactivité maximale** | Anticiper, suggérer, challenger, rappeler — sans attendre |
| **3** | **Intimité totale** | Aucune limite d'accès pour une efficacité maximale |
| **4** | **Apprentissage progressif** | Seuils de confiance appris, pas de règles rigides |
| **5** | **Construction propre** | Lent mais bien construit dès le début |

📖 **Document fondateur** : [DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md) — Capture l'âme de Scapin, les fondements théoriques complets, et les décisions de conception.

---

## 🔄 La Boucle d'Amélioration Continue

Le système s'améliore via un cycle vertueux centré sur le journaling quotidien :

```
Journée vécue
     ↓
Scapin pré-remplit le journal (ce qu'il sait)
     ↓
Vous complétez et corrigez (~15 min)
     ↓
Enrichissement des fiches (personnes, projets, décisions)
     ↓
Meilleure analyse future
     ↓
Suggestions plus pertinentes
     ↓
Feedback via journaling suivant
     ↓
Amélioration du système → Répéter
```

**Information en 3 Couches** :
| Niveau | Contenu | Temps | Usage |
|--------|---------|-------|-------|
| **1** | Résumé actionnable | 30s | Décision rapide |
| **2** | Contexte et options | 2 min | Choix informé |
| **3** | Détails complets | Variable | Auto-alimentation Scapin |

---

## ✨ Capacités Actuelles

### Production Ready (v1.0.0-alpha)

| Fonctionnalité | Statut | Description |
|----------------|--------|-------------|
| **Traitement Email Intelligent** | ✅ | Classification IA, multi-comptes, traitement par lots |
| **Menu Interactif** | ✅ | Navigation clavier, sélection comptes, gestion file de révision |
| **Multi-Comptes Email** | ✅ | Gestion illimitée de comptes avec configs séparées |
| **File de Révision** | ✅ | Approuver/modifier/rejeter les décisions IA |
| **Intégration Tâches** | ✅ | Création auto OmniFocus via MCP |
| **Système d'Événements** | ✅ | Pub/sub thread-safe avec 17 types d'événements |
| **Monitoring Santé** | ✅ | Checks IMAP, API IA, disque, file |
| **Récupération Erreurs** | ✅ | Backoff exponentiel, protection timeout, cache LRU |
| **Suivi Décisions** | ✅ | Stockage SQLite avec contexte |
| **Architecture Cognitive** | ✅ | Modules valets complets (Phase 0.5) |

**Qualité** : 967 tests, 95% couverture, 100% pass rate
**Code** : Score 10/10 (0 ruff warnings)

### Architecture Cognitive (Phase 0.5 — ✅ Complète)

Scapin utilise une **boucle cognitive itérative** — pas une IA one-shot, mais un raisonnement multi-étapes véritable :

```
Événement → Trivelin → Sancho ↔ Passepartout → Planchet → Figaro → Sganarelle
                         ↑                                             ↓
                         └─────────── Boucle d'Apprentissage ─────────┘
```

**Raisonnement Multi-Passes de Sancho** (jusqu'à 5 itérations) :

| Passe | Processus | Confiance Cible | Temps |
|-------|-----------|-----------------|-------|
| **1. Analyse Initiale** | Comprendre l'événement | ~60-70% | 2-3s |
| **2. Enrichissement Contexte** | Interroger Passepartout | ~75-85% | 3-5s |
| **3. Raisonnement Profond** | Inférence multi-étapes, chaînes "si X alors Y" | ~85-92% | 2-4s |
| **4. Validation** | Consensus multi-provider (Claude + GPT-4o) | ~90-96% | 3-5s |
| **5. Clarification Utilisateur** | Demander quand incertain | ~95-99% | async |

**Arrêt** : Confiance ≥ 95% OU maximum d'itérations atteint

**Exemple concret** : Email du comptable avec tableur
- Passe 1 : "Email de Marie avec pièce jointe" (65%)
- Passe 2 : Passepartout trouve "Marie = Comptable, projet Budget Q2" (82%)
- Passe 3 : Infère deadline des notes, planifie actions (89%)
- Passe 4 : GPT-4o valide, suggère emplacement fichier (94.5%)
- Passe 5 : Demande "Marquer prioritaire ?" → "Non" (97%)
- Résultat : 5 actions exécutées parfaitement

---

## 🎪 L'Équipe des Valets

Scapin orchestre une équipe de modules spécialisés, chacun inspiré d'un valet littéraire célèbre :

| Valet | Origine Littéraire | Module | Spécialité |
|-------|-------------------|--------|------------|
| **Trivelin** | Marivaux, *L'Île des esclaves* | `src/trivelin/` | 🔍 **Triage** — Réception et classification des événements |
| **Sancho** | Cervantes, *Don Quichotte* | `src/sancho/` | 🧠 **Sagesse** — Raisonnement itératif multi-passes |
| **Passepartout** | Verne, *Le Tour du monde* | `src/passepartout/` | 🧭 **Navigation** — Recherche dans la base de connaissances |
| **Planchet** | Dumas, *Les Trois Mousquetaires* | `src/planchet/` | 📅 **Planification** — Conception des plans d'action |
| **Figaro** | Beaumarchais, *Le Barbier de Séville* | `src/figaro/` | 🎼 **Orchestration** — Exécution coordonnée des actions |
| **Sganarelle** | Molière | `src/sganarelle/` | 📚 **Apprentissage** — Amélioration par l'expérience |
| **Jeeves** | Wodehouse | `src/jeeves/` | 🎩 **Service** — Interface API élégante |

### Workflow Collaboratif

```
1. TRIVELIN reçoit et trie l'événement
        ↓
2. SANCHO raisonne (jusqu'à 5 passes)
        ↓ ← consulte → PASSEPARTOUT (base de connaissances)
        ↓
3. PLANCHET conçoit un plan d'action
        ↓
4. FIGARO orchestre l'exécution
        ↓
5. SGANARELLE apprend du résultat → enrichit PASSEPARTOUT
        ↑
6. JEEVES fournit l'API pour web/mobile
```

**Structure du Projet** :
```
scapin/
├── src/
│   ├── trivelin/        # Perception & triage
│   ├── sancho/          # Moteur de raisonnement
│   ├── passepartout/    # Base de connaissances (Markdown + Git + FAISS)
│   ├── planchet/        # Moteur de planification
│   ├── figaro/          # Orchestration des actions (DAG)
│   ├── sganarelle/      # Apprentissage & feedback
│   ├── jeeves/          # Couche API (FastAPI + WebSockets)
│   └── core/            # Infrastructure partagée
├── tests/               # 967 tests, 95% couverture
└── docs/                # Documentation complète
```

---

## 🚀 Démarrage Rapide

### Prérequis

- Python 3.9+
- Git
- Compte email (iCloud, Gmail, etc.)
- Clé API Anthropic (Claude)

### Installation

```bash
# Cloner le dépôt
git clone https://github.com/johanlb/scapin.git
cd scapin

# Créer l'environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# Configurer
cp .env.example .env
# Éditer .env avec vos identifiants
```

### Utilisation

```bash
# Lancer le menu interactif
python3 scapin.py

# Ou commandes CLI directes
python3 scapin.py health      # Vérification santé système
python3 scapin.py process     # Traiter les emails
python3 scapin.py review      # Réviser les décisions en attente
```

---

## 📚 Documentation

### Documents Fondateurs

| Document | Description |
|----------|-------------|
| **[DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md)** | 🎯 **Document fondateur** — Principes philosophiques, fondements théoriques (Extended Mind, Stiegler, Wegner), vision du partenariat cognitif |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Architecture cognitive complète — Comment l'équipe des valets fonctionne |
| **[ROADMAP.md](ROADMAP.md)** | Phases de développement, priorités, calendrier (Q1-Q4 2026) |

### Documents Techniques

| Document | Description |
|----------|-------------|
| **[CLAUDE.md](CLAUDE.md)** | Contexte de session pour Claude Code — État actuel du projet |
| **[MIGRATION.md](MIGRATION.md)** | Migration depuis PKM System vers Scapin |
| **[BREAKING_CHANGES.md](BREAKING_CHANGES.md)** | Changements d'API et guides de migration |
| **[docs/api/](docs/api/)** | Documentation de référence API |

### Concepts Clés

- **Architecture Valet** : Comment Trivelin, Sancho, Passepartout collaborent
- **Raisonnement Multi-Passes** : Pourquoi 10-20s pour de meilleures décisions
- **Boucle Cognitive** : Événement → Perception → Raisonnement → Planification → Action → Apprentissage
- **Pharmacologie** : Comment Scapin augmente vos capacités sans les remplacer
- **Information en Couches** : Niveau 1 (30s) → Niveau 2 (2min) → Niveau 3 (complet)

---

## 🛣️ Feuille de Route

### Phases Complétées ✅

| Phase | Nom | Statut |
|-------|-----|--------|
| **0** | Fondations | ✅ Structure, config, logging, CLI |
| **1** | Intelligence Email | ✅ Multi-comptes, classification IA, récupération erreurs |
| **2** | Expérience Interactive | ✅ Menu, file révision, UI multi-comptes |
| **0.5** | Architecture Cognitive | ✅ Tous les modules valets implémentés |
| **0.6** | Refactoring Valet | ✅ Migration src/ai/ → sancho, src/cli/ → jeeves, email_processor → trivelin |

### Phases en Cours et Planifiées 📅

| Phase | Nom | Période | Focus |
|-------|-----|---------|-------|
| **1.0** | Trivelin Email | Q1 2026 | 🏗️ Traitement email intelligent multi-passes |
| **1.1** | Journaling Email | Q1 2026 | Feedback loop, pré-remplissage journal |
| **1.2** | Intégration Teams | Q2 2026 | Messages, réponses, appels |
| **1.3** | Intégration Calendrier | Q2 2026 | Événements, disponibilités |
| **1.4** | Système de Briefing | Q2 2026 | Briefing matin, pré-réunion |
| **0.7** | API Jeeves | Q3 2026 | FastAPI REST + WebSockets |
| **0.8** | Interface Web | Q3 2026 | SvelteKit + TailwindCSS |
| **0.9** | PWA Mobile | Q4 2026 | Progressive Web App |

---

## 🧪 Tests

```bash
# Tous les tests
pytest tests/ -v

# Par module
pytest tests/unit/ -v
pytest tests/integration/ -v

# Avec couverture
pytest tests/ --cov=src --cov-report=html
```

**Couverture actuelle** : 95%+ (967 tests)

---

## 🎨 Stack Technologique

### Backend

| Composant | Technologie | Usage |
|-----------|-------------|-------|
| **Langage** | Python 3.11+ | Runtime principal |
| **Validation** | Pydantic | Configuration type-safe |
| **CLI** | Typer + Rich | Interface ligne de commande |
| **Tests** | pytest | 967 tests, 95% couverture |
| **Événements** | EventBus custom | Pub/sub thread-safe |

### IA & Intelligence

| Composant | Technologie | Usage |
|-----------|-------------|-------|
| **IA Principale** | Claude (Anthropic) | Raisonnement Sonnet 4.5 |
| **Consensus** | GPT-4o (OpenAI) | Validation Passe 4 |
| **Embeddings** | sentence-transformers | Recherche sémantique |
| **Vector DB** | FAISS → ChromaDB | Similarité rapide |

### Stockage

| Composant | Technologie | Usage |
|-----------|-------------|-------|
| **Notes** | Markdown + YAML | Base de connaissances lisible |
| **Versioning** | Git | Commits auto, historique complet |
| **État** | SQLite | Suivi décisions, erreurs |
| **Graphe** | NetworkX | Relations (Phase 5) |

### Intégrations

| Composant | Technologie | Usage |
|-----------|-------------|-------|
| **Email** | IMAP | Traitement multi-comptes |
| **Tâches** | OmniFocus MCP | Création et gestion |
| **Credentials** | macOS Keychain | Stockage sécurisé |

---

## 🙏 Remerciements

### Inspiration Littéraire

Les valets de la comédie classique qui ont inspiré l'architecture :

- **Molière** — Scapin, Sganarelle
- **Marivaux** — Trivelin
- **Cervantes** — Sancho Panza
- **Dumas** — Planchet
- **Beaumarchais** — Figaro
- **Wodehouse** — Jeeves
- **Verne** — Passepartout

### Fondements Théoriques

- **Clark & Chalmers** — Extended Mind Thesis
- **Wegner** — Mémoire Transactive
- **Stiegler** — Pharmacologie de la technique
- **Sparrow et al.** — Effet Google
- **Tiago Forte** — Building a Second Brain
- **Sönke Ahrens** — Méthode Zettelkasten

### Technologies

- **Anthropic** — Claude AI
- **OpenAI** — GPT-4o
- **sentence-transformers** — Embeddings sémantiques

---

## 🔄 Migration depuis PKM System

| Aspect | PKM System | Scapin |
|--------|-----------|--------|
| **Identité** | Processeur email | Gardien cognitif |
| **Modules** | Génériques | Thème valet |
| **Version** | v3.1.0 (final) | v1.0.0-alpha |
| **Dépôt** | [Archivé](https://github.com/johanlb/pkm-system) | [Actif](https://github.com/johanlb/scapin) |
| **Données** | ✅ Compatible | ✅ Copier `.env` et `data/` |

Voir **[MIGRATION.md](MIGRATION.md)** pour les détails.

---

## 📝 Licence

MIT License — Voir fichier LICENSE

---

## 📞 Contact

**Johan Le Bail**  
GitHub : [@johanlb](https://github.com/johanlb)

---

**🎭 Construit avec intelligence et élégance — Votre Scapin personnel vous attend.**

*"Le valet qui peut tout faire vaut plus que le maître qui ne peut rien."* — Molière
