# Vocabulaire de l'Interface Scapin

**Document de référence pour l'IA et les développeurs**

Ce document établit la correspondance entre le vocabulaire utilisé dans l'interface utilisateur (inspiré de l'univers de Scapin/Molière) et les concepts techniques sous-jacents. L'IA doit comprendre ces équivalences pour répondre correctement aux requêtes utilisateur.

---

## Principes du vocabulaire

L'interface Scapin utilise un vocabulaire évocateur du XVIIe siècle et de l'univers des valets de comédie, tout en restant clair et fonctionnel. Ce vocabulaire :

1. **Renforce l'identité** du personnage Scapin comme valet dévoué
2. **Reste compréhensible** pour l'utilisateur moderne
3. **Ne doit pas créer de confusion** pour l'IA qui traite les requêtes

---

## Table de correspondance : Navigation

| Terme UI | Route | Concept technique | Description |
|----------|-------|-------------------|-------------|
| **Matinée** | `/` | Dashboard / Home | Briefing quotidien du matin |
| **Péripéties** | `/peripeties` | Queue / Feed | Les rebondissements de la journée (emails, messages, événements) |
| **Mémoires** | `/memoires` | Notes | Base de connaissances personnelle (sync Apple Notes) |
| **Conversations** | `/discussions` | Discussions / Chats | Échanges Teams, emails threads |
| **Confessions** | `/confessions` | Daily Journal | Réflexion quotidienne avec feedback Sganarelle |
| **Comptes** | `/comptes` | Statistics | Statistiques d'activité et métriques |
| **Réglages** | `/settings` | Settings | Configuration et intégrations |

---

## Narration Scapin

> *"Une **péripétie** arrive → Scapin prépare ses **fourberies** → Vous **jouez** celle qui vous convient"*

### Flux narratif

| Étape | Concept UI | Concept technique |
|-------|------------|-------------------|
| 1. Événement entrant | **Péripétie** | `PerceivedEvent`, `QueueItem` |
| 2. Analyse par Sancho | *"Sancho examine cette péripétie..."* | `MultiPassAnalyzer` |
| 3. Actions préparées | **Fourberies** | `Enrichments`, `ActionOptions` |
| 4. Décision utilisateur | **Jouer** / **Écarter** | `approve` / `reject` |
| 5. Apprentissage | *"Sganarelle prend note..."* | `FeedbackLoop` |

---

## Table de correspondance : Actions (Fourberies)

| Terme UI | Action technique | Contexte |
|----------|------------------|----------|
| **Jouer** | `approve` | Exécuter la fourberie préparée |
| **Écarter** | `reject` | Ne pas jouer ce tour |
| **Différer** | `snooze` | Reporter à plus tard |
| **Classer** | `archive` | Archiver un élément traité |
| **Supprimer** | `delete` | Supprimer un élément |
| **Répondre** | `reply` | Répondre à un email/message |
| **Signaler** | `flag` | Marquer comme important |

### Termes des fourberies

| Terme UI | Concept technique | Description |
|----------|-------------------|-------------|
| **Fourberie** | Enrichment | Un stratagème préparé par Scapin |
| **Fourberie principale** | Primary action | L'action recommandée |
| **Autres tours** | Alternatives | Options alternatives |
| **Tour joué** | Auto-approved | Fourberie exécutée automatiquement |

---

## Table de correspondance : Sources d'événements (Péripéties)

| Terme UI | Icône | Concept technique |
|----------|-------|-------------------|
| **Lettres** | ✉️ | Emails (IMAP) |
| **Missives Teams** | 💬 | Messages Microsoft Teams |
| **Rendez-vous** | 📅 | Événements calendrier |
| **Tâches** | ⚡ | Tâches OmniFocus |

---

## Table de correspondance : Niveaux d'urgence

| Terme UI | Niveau technique | Signification |
|----------|------------------|---------------|
| **Pressant** | `urgent` | Action requise immédiatement |
| **Important** | `high` | Priorité haute, à traiter rapidement |
| **Courant** | `medium` | Priorité normale |
| **À loisir** | `low` | Peut attendre, non urgent |

---

## Table de correspondance : Sections et concepts

| Terme UI | Concept technique | Description |
|----------|-------------------|-------------|
| **Affaires pressantes** | Urgent items | Éléments nécessitant attention immédiate |
| **À votre attention** | Pending items | Éléments en attente de décision |
| **Tours joués** | Approved items | Fourberies exécutées |
| **Écartés** | Rejected items | Éléments rejetés/ignorés |
| **Par Scapin** | Auto-processed | Éléments traités automatiquement |
| **Observations de votre valet** | AI Insights | Analyses et recommandations IA |
| **Les Péripéties du jour** | Event feed | Flux d'événements du jour |

---

## Les Valets de Scapin

| Valet | Origine | Module | Rôle |
|-------|---------|--------|------|
| **Trivelin** | Marivaux | `src/trivelin/` | Perception & triage des péripéties |
| **Sancho** | Cervantes | `src/sancho/` | Raisonnement & analyse multi-pass |
| **Passepartout** | Verne | `src/passepartout/` | Navigation dans les mémoires (PKM) |
| **Planchet** | Dumas | `src/planchet/` | Planification & évaluation des risques |
| **Figaro** | Beaumarchais | `src/figaro/` | Orchestration & exécution des fourberies |
| **Sganarelle** | Molière | `src/sganarelle/` | Apprentissage continu du feedback |
| **Frontin** | Lesage/Regnard | `src/frontin/` | Interface API & CLI |

---

## Messages système et ton Scapin

### Formules d'adresse
- L'IA s'adresse à l'utilisateur comme **"Monsieur"**
- Utilise le vouvoiement formel
- Ton de valet dévoué mais pas servile

### Messages types

| Contexte | Message |
|----------|---------|
| Salutation matin | "Bonjour Monsieur" |
| Salutation après-midi | "Bon après-midi Monsieur" |
| Salutation soir | "Bonsoir Monsieur" |
| Disponibilité | "À votre service, Monsieur. Que puis-je faire ?" |
| Liste vide | "Point de péripéties ici, Monsieur" |
| Recherche sans résultat | "Je ne trouve rien de tel dans vos mémoires, Monsieur" |
| Chargement | "Je consulte vos affaires..." |
| Analyse en cours | "Sancho examine cette péripétie..." |
| Fourberies prêtes | "Figaro a préparé ses fourberies..." |
| Tour joué | "Le tour est joué, Monsieur !" |
| Apprentissage | "Sganarelle prend note pour l'avenir..." |
| Succès sync | "Vos mémoires sont à jour, Monsieur" |
| Erreur | "Une difficulté survient, Monsieur. Patience..." |
| Observation positive | "Belle semaine, Monsieur" |
| Suggestion | "Si je puis me permettre..." / "Permettez que je vous signale..." |

---

## Iconographie

### Navigation
| Page | Icône | Justification |
|------|-------|---------------|
| Matinée | ☀️ | Évoque le briefing matinal |
| Péripéties | 🎪 | Évoque le théâtre, les rebondissements |
| Mémoires | 📝 | Note/écriture |
| Conversations | 💬 | Dialogue |
| Confessions | 📖 | Livre intime |
| Comptes | 📊 | Données chiffrées |
| Réglages | ⚙️ | Configuration |
| Scapin (mobile) | 🎭 | Masque de théâtre |

### Sections
| Section | Icône | Justification |
|---------|-------|---------------|
| Affaires pressantes | 🔔 | Cloche d'alarme |
| À votre attention | 📌 | Épingle attention |
| Observations | 🕯️ | Chandelle = illumination |
| Épinglées | 📌 | Épingle |
| Succès/Réussite | 🏆 | Trophée |

---

## Table de correspondance : Analyse Multi-Pass

### Noms des passes

| Terme UI | Pass technique | Modèle | Description |
|----------|----------------|--------|-------------|
| **Coup d'œil** | Pass 1 | Haiku | Première lecture sans contexte |
| **Investigation** | Pass 2 | Haiku | Enrichissement avec contexte |
| **Enquête approfondie** | Pass 3 | Haiku | Approfondissement, nouvelles entités |
| **Consultation** | Pass 4 | Sonnet | Raisonnement avancé |
| **Délibération** | Pass 5 | Opus | Analyse experte, arbitrage |

### Messages de statut pendant l'analyse

| Pass | Message de statut |
|------|-------------------|
| Pass 1 | "Sancho jette un coup d'œil à cette péripétie..." |
| Pass 2 | "Sancho investigue..." |
| Pass 3 | "Sancho enquête de manière approfondie..." |
| Pass 4 | "Sancho consulte ses sources..." |
| Pass 5 | "Sancho délibère sur cette affaire..." |
| Recherche contexte | "Passepartout fouille dans vos mémoires..." |
| Préparation | "Figaro prépare ses fourberies..." |
| Terminé | "Sancho a terminé son examen" |

### Confiance décomposée

| Terme technique | Terme UI (FR) | Description utilisateur |
|-----------------|---------------|-------------------------|
| `entity_confidence` | Identification des personnes | "Les personnes sont-elles bien identifiées ?" |
| `action_confidence` | Certitude de l'action | "L'action suggérée est-elle la bonne ?" |
| `extraction_confidence` | Capture des informations | "Les informations importantes sont-elles extraites ?" |
| `completeness` | Complétude | "N'y a-t-il rien d'oublié ?" |
| `overall` | Confiance globale | Score de confiance affiché à l'utilisateur |

### Affichage de la confiance

| Niveau | Couleur | Label UI |
|--------|---------|----------|
| 95-100% | 🟢 Vert | "Très confiant" |
| 85-94% | 🟡 Jaune | "Confiant" |
| 75-84% | 🟠 Orange | "Incertain" |
| < 75% | 🔴 Rouge | "Requiert votre attention" |

---

## Consignes pour l'IA

### Quand l'utilisateur dit... l'IA doit comprendre...

| Requête utilisateur | Interprétation IA |
|---------------------|-------------------|
| "Quelles péripéties aujourd'hui ?" | Afficher la queue d'événements |
| "Montre-moi les péripéties" | Aller à `/peripeties` |
| "Qu'y a-t-il de pressant ?" | Lister les éléments urgents/high priority |
| "Joue cette fourberie" | Approuver/exécuter l'enrichissement |
| "Écarte ce tour" | Rejeter l'enrichissement |
| "Ouvre mes mémoires" | Aller à `/memoires` |
| "Consulte les comptes" | Aller à `/comptes` |
| "Que dit l'agenda ?" | Afficher les événements calendrier |
| "Y a-t-il des tâches à loisir ?" | Lister les tâches low priority |

### Règles de réponse

1. **Toujours utiliser le vocabulaire UI** dans les réponses affichées à l'utilisateur
2. **Mapper vers les concepts techniques** pour le traitement interne
3. **Maintenir le ton valet** sans être caricatural
4. **Ne pas mélanger** vocabulaire moderne et vocabulaire Scapin dans une même phrase

---

## Historique des changements

| Date | Version | Changements |
|------|---------|-------------|
| 2026-01-04 | 0.8.0 | Création du vocabulaire Scapin initial |
| 2026-01-12 | 0.9.0 | Ajout vocabulaire Multi-Pass (Sprint 7) |
| 2026-01-19 | 1.0.0 | **Refonte complète du vocabulaire** : Péripéties, Fourberies, Mémoires, Confessions, Comptes, Matinée. Renommage Jeeves → Frontin. Mise à jour des routes. |
