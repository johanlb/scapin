# 2. Briefing

Le **Briefing** est votre point d'entrée quotidien dans Scapin. Il vous présente une vue synthétique de ce qui nécessite votre attention.

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

## Conseils

1. **Consultez le briefing chaque matin** — 2 minutes pour planifier votre journée
2. **Préparez vos réunions** — Cliquez sur le briefing pré-réunion 15 min avant
3. **Traitez les urgents d'abord** — La section rouge nécessite une action immédiate
