# 2. Briefing

Le **Briefing** est votre point d'entrée quotidien dans Scapin. Il vous présente une vue synthétique de ce qui nécessite votre attention.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  BRIEFING                                     Lundi 20 janvier 2026   [⚙]   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  🔴 URGENT (3)                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ 📧 Facture impayée - Relance                          ⏰ il y a 2j    │ │
│  │ 📅 Réunion Budget Q1                                  ⏰ dans 30min   │ │
│  │ 💬 @mention de Jean dans #projet-alpha                ⏰ il y a 1h    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  📅 AGENDA DU JOUR                                                          │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  09:00 - 10:00  │ Réunion Budget Q1          │ 👥 Marie, Jean    [📄] │ │
│  │  11:30 - 12:00  │ Point hebdo équipe         │ 👥 Équipe tech    [📄] │ │
│  │  14:00 - 15:30  │ Workshop Design            │ 👥 Design team         │ │
│  │  ⚠️ 15:00 - 16:00  │ Call client (conflit!)  │ 👥 Client ABC          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  📊 STATISTIQUES                                                            │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐             │
│  │ 📧 Emails    │ 💬 Teams     │ 📝 Notes     │ ✅ Tâches    │             │
│  │    12        │    5         │    3         │    7         │             │
│  │  à traiter   │  non lus     │  à réviser   │  aujourd'hui │             │
│  └──────────────┴──────────────┴──────────────┴──────────────┘             │
│                                                                              │
│  [📄] = Briefing pré-réunion disponible                                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Briefing Matinal

### Accès

- **Web** : Page d'accueil (`/`)
- **CLI** : `scapin briefing --morning`

### Contenu

Le briefing matinal affiche :

#### 1. Éléments Urgents

Items nécessitant une attention immédiate :
- Emails urgents non traités
- Messages Teams importants
- Événements calendrier imminents

Chaque élément affiche :
- **Titre** : Sujet ou nom
- **Source** : Email, Teams, Calendrier
- **Urgence** : Score de priorité
- **Temps** : Depuis quand / dans combien de temps

#### 2. Agenda du Jour

Vos événements calendrier pour les prochaines 24h :
- Heure de début/fin
- Titre de la réunion
- Participants
- Conflits éventuels (alertes orange)

#### 3. Statistiques

Aperçu rapide :
- Emails en attente
- Messages Teams non lus
- Notes à réviser

#### 4. Questions Stratégiques Orphelines (v3.2)

Les questions générées lors de l'analyse des emails qui n'ont pas de note cible apparaissent dans une section dédiée :

```
❓ QUESTIONS STRATÉGIQUES (2)
┌────────────────────────────────────────────────────────────────────────┐
│ 🎯 Quelle stratégie pour traiter ces 9229 Smart Matches ?             │
│    Catégorie: organisation • Source: mousqueton                        │
│    Via: "MyHeritage - Nouveaux Smart Matches disponibles"              │
│                                                          [✓ Résoudre]  │
├────────────────────────────────────────────────────────────────────────┤
│ ⚙️ Un système de traitement batch peut-il être mis en place ?         │
│    Catégorie: processus • Source: planchet                             │
│    Via: "MyHeritage - Nouveaux Smart Matches disponibles"              │
│                                                          [✓ Résoudre]  │
└────────────────────────────────────────────────────────────────────────┘
```

Ces questions :
- Sont générées par les valets mais n'ont pas de note thématique existante
- Nécessitent votre réflexion pour décider de l'action (créer une note, ignorer, etc.)
- Peuvent être résolues directement depuis le briefing

---

## Briefing Pré-Réunion

### Accès

Cliquez sur l'icône 📄 sur un événement calendrier.

### Contenu

Avant une réunion, Scapin prépare :

#### 1. Informations Réunion

- Titre, heure, durée
- Lien de connexion (Teams/Zoom/Meet)
- Agenda (si fourni)

#### 2. Participants

Pour chaque participant :
- Nom et email
- Dernières interactions (emails, messages)
- Notes associées dans votre base

#### 3. Contexte

- Emails récents liés au sujet
- Notes pertinentes
- Historique des échanges

#### 4. Points de Discussion Suggérés

Scapin suggère des sujets basés sur :
- Threads email non résolus
- Questions en suspens
- Actions promises

---

## Détection de Conflits

Scapin détecte automatiquement :

### Chevauchements

Deux réunions au même moment :
- **Full overlap** : Conflit total (rouge)
- **Partial overlap** : Conflit partiel (orange)

### Temps de Trajet

Si deux réunions consécutives sont en lieux différents :
- Alerte si le gap est < 30 minutes
- Non applicable pour les réunions en ligne

---

## Notifications

### Types

| Type | Description |
|------|-------------|
| **Urgent** | Action requise immédiatement |
| **Important** | À traiter dans la journée |
| **Info** | Pour information |

### Gestion

- Cliquer sur la cloche pour ouvrir le panneau
- Marquer comme lu individuellement ou en masse
- Filtrer par type

---

## Personnalisation

### Heures de Briefing

Dans Settings > Briefing :
- Heures à regarder en arrière (défaut : 12h)
- Heures à regarder en avant (défaut : 24h)

### Sources

Activer/désactiver les sources :
- Email
- Teams
- Calendrier
- OmniFocus (si configuré)

---

## Filage (v2.6)

Le **Filage** est votre briefing matinal de révision, préparé automatiquement à 6h. Il vous présente jusqu'à **20 Lectures** prioritaires pour maintenir vos connaissances fraîches.

### Accès

- **Web** : `/briefing/filage` ou onglet "Filage" dans le briefing
- **CLI** : `scapin filage`
- **API** : `GET /api/briefing/filage`

### Priorités de Sélection

Le Filage sélectionne les notes par ordre de priorité :

| Priorité | Type | Description | Max |
|----------|------|-------------|-----|
| **1** | 🔴 Questions | Notes avec questions en attente | 5 |
| **2** | 📅 Événements | Notes liées aux réunions du jour | 5 |
| **3** | 📚 SM-2 Due | Notes dues selon l'algorithme Lecture | 8 |
| **4** | ✨ Retouchées | Notes récemment améliorées par l'IA | 2 |

### Interface Filage

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  FILAGE                                      Lundi 20 janvier 2026    [⚙]   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  📊 RÉSUMÉ                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  20 Lectures  │  3 Questions  │  2 Événements  │  15 Notes dues       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  🔴 QUESTIONS EN ATTENTE (3)                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ 👤 Marie Dupont                 2 questions   │ Qualité: 65%   [📖]  │ │
│  │ 📁 Projet Alpha                 1 question    │ Qualité: 72%   [📖]  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  📅 LIÉES AUX ÉVÉNEMENTS (2)                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ 👤 Jean Martin                  Réunion 10h   │ Qualité: 80%   [📖]  │ │
│  │ 📁 Budget Q1                    Réunion 14h   │ Qualité: 55%   [📖]  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  📚 À RÉVISER (15)                                                          │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ 👤 Pierre Durand               Due: 2h ago    │ Qualité: 78%   [📖]  │ │
│  │ ...                                                                    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  [📖] = Démarrer Lecture                                                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Session de Lecture

Cliquer sur [📖] démarre une **session de Lecture** :

1. **Affichage** : La note complète est présentée
2. **Questions** : Si présentes, les questions apparaissent en bas
3. **Réponses** : Vous pouvez répondre aux questions (optionnel)
4. **Notation** : Vous notez la qualité de votre rappel (0-5)

| Note | Signification | Intervalle |
|------|---------------|------------|
| **5** | Rappel parfait | × 2.5 EF |
| **4** | Bonne mémoire | × 2.0 EF |
| **3** | Avec effort | × 1.5 EF |
| **2** | Difficile | Reset 24h |
| **1** | Vague souvenir | Reset 24h |
| **0** | Oubli total | Reset 24h |

### Questions pour Johan

Scapin peut injecter des **questions personnalisées** dans vos notes lors de la Retouche IA. Ces questions apparaissent dans la section `## Questions pour Johan` et visent à :

- Combler les lacunes d'information
- Approfondir votre compréhension
- Vous inciter à enrichir la note

**Exemple** :
```markdown
## Questions pour Johan
- Quel est le budget exact du projet ?
- Quelle est la deadline finale ?
```

Lors d'une Lecture, vous pouvez répondre directement à ces questions. Vos réponses sont intégrées à la note.

---

## Conseils

1. **Consultez le briefing chaque matin** — 2 minutes pour planifier votre journée
2. **Préparez vos réunions** — Cliquez sur le briefing pré-réunion 15 min avant
3. **Traitez les urgents d'abord** — La section rouge nécessite une action immédiate
4. **Faites votre Filage** — 10 minutes de Lectures le matin maintiennent vos connaissances fraîches
