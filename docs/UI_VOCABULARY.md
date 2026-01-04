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

| Terme UI | Concept technique | Description |
|----------|-------------------|-------------|
| **Rapport** | Dashboard / Home | Page d'accueil avec briefing quotidien |
| **Courrier** | Flux / Feed | Timeline de tous les événements (emails, messages, etc.) |
| **Carnets** | Notes | Base de connaissances personnelle (sync Apple Notes) |
| **Conversations** | Discussions / Chats | Échanges Teams, emails threads |
| **Journal** | Daily Journal | Réflexion quotidienne avec feedback Sganarelle |
| **Registres** | Statistics | Statistiques d'activité et métriques |
| **Réglages** | Settings | Configuration et intégrations |

---

## Table de correspondance : Sources d'événements

| Terme UI | Icône | Concept technique |
|----------|-------|-------------------|
| **Lettres** | ✉️ | Emails (IMAP) |
| **Teams** | 💬 | Messages Microsoft Teams |
| **Agenda** | 📅 | Événements calendrier |
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

## Table de correspondance : Actions

| Terme UI | Action technique | Contexte |
|----------|------------------|----------|
| **Classer** | `archive` | Archiver un élément traité |
| **Supprimer** | `delete` | Supprimer un élément |
| **Répondre** | `reply` | Répondre à un email/message |
| **Signaler** | `flag` | Marquer comme important |
| **Reporter** | `defer` | Différer le traitement |
| **Ignorer** | `reject` | Ne rien faire, écarter |
| **Passer** | `skip` | Passer au suivant sans action |
| **Plus tard** | `snooze` | Reporter en fin de file |
| **Rédiger** | `create_note` | Créer une nouvelle note |
| **Consigner** | `create_journal_entry` | Créer une entrée de journal |
| **Recevoir** | `import` | Importer des fichiers |
| **Établir** | `connect` | Connecter une intégration |
| **Ajuster** | `configure` | Configurer une intégration |

---

## Table de correspondance : Sections et concepts

| Terme UI | Concept technique | Description |
|----------|-------------------|-------------|
| **Affaires pressantes** | Urgent items | Éléments nécessitant attention immédiate |
| **À votre attention** | Pending items | Éléments en attente de décision |
| **Traités** | Approved items | Éléments traités/approuvés |
| **Écartés** | Rejected items | Éléments rejetés/ignorés |
| **Par Scapin** | Auto-processed | Éléments traités automatiquement |
| **Observations de votre valet** | AI Insights | Analyses et recommandations IA |
| **Le Courrier du jour** | Event feed | Flux d'événements du jour |
| **Vos Registres** | Statistics dashboard | Tableau de bord statistiques |
| **Pli** | Email/Message | Un email ou message dans la queue |

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
| Liste vide | "Point d'affaires ici, Monsieur" |
| Recherche sans résultat | "Je ne trouve rien de tel dans vos papiers, Monsieur" |
| Chargement | "Je consulte vos affaires..." |
| Succès sync | "Vos papiers sont à jour, Monsieur" |
| Erreur | "Une difficulté survient, Monsieur. Patience..." |
| Observation positive | "Belle semaine, Monsieur" |
| Suggestion | "Si je puis me permettre..." / "Permettez que je vous signale..." |

---

## Iconographie

### Navigation
| Page | Icône | Justification |
|------|-------|---------------|
| Rapport | ☀️ | Évoque le briefing matinal |
| Courrier | 📜 | Parchemin/scroll d'époque |
| Carnets | 📝 | Note/écriture |
| Conversations | 💬 | Dialogue |
| Journal | 📖 | Livre/registre |
| Registres | 📊 | Données chiffrées |
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

## Consignes pour l'IA

### Quand l'utilisateur dit... l'IA doit comprendre...

| Requête utilisateur | Interprétation IA |
|---------------------|-------------------|
| "Montre-moi le courrier" | Afficher le flux d'événements |
| "Qu'y a-t-il de pressant ?" | Lister les éléments urgents/high priority |
| "Classe cette lettre" | Archiver cet email |
| "Ouvre mes carnets" | Aller à la page Notes |
| "Consulte les registres" | Afficher les statistiques |
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

