# 3. Péripéties

Les **Péripéties** sont le centre de traitement de vos emails et messages. C'est ici que Scapin vous présente les éléments analysés pour validation.

> **Note v2.4** : Cette section a été renommée de "Flux" à "Péripéties" pour mieux refléter le concept littéraire du projet.

---

## Principe

```
Email arrive → Scapin analyse → Proposition d'action → Vous validez → Exécution
```

Scapin ne fait **jamais** d'action sans votre approbation (sauf si la confiance dépasse 90%).

---

## Interface

### Liste des Items

Chaque item affiche :

- **Expéditeur** : Nom et email
- **Sujet** : Titre de l'email
- **Extrait** : Premiers mots du contenu
- **Action proposée** : Archive, Répondre, Tâche...
- **Confiance** : Score IA (0-100%)
- **Destination** : Dossier cible

### Niveaux d'Affichage

| Mode | Information |
|------|-------------|
| **Compact** | Sujet, expéditeur, action |
| **Normal** | + extrait, confiance, entités |
| **Enrichi** | + raisonnement IA complet |

Basculer avec le bouton "Enrichir" / "Vue simple".

---

## Actions

### Approuver

- **Bouton** : ✓ Approuver (vert)
- **Swipe** : Droite (mobile)
- **Raccourci** : `Enter` (après sélection)

L'email est traité selon l'action proposée.

### Rejeter

- **Bouton** : ✗ Rejeter (rouge)
- **Swipe** : Gauche (mobile)
- **Raccourci** : `Backspace`

L'email reste dans l'inbox, non traité.

### Ré-analyser (Autre)

- **Bouton** : 💡 Autre / Ré-analyser
- Permet de donner une **instruction spécifique** (ex: "Extrais aussi le numéro de facture")
- Déclenche un second passage de l'IA (Passe de Raffinement)
- Utile quand l'analyse automatique a manqué un détail important.

### Modifier

- **Bouton** : ✎ Modifier
- Ajuster l'action ou la destination avant approbation

### Snooze (Reporter)

- **Bouton** : ⏰ Snooze
- Choisir : 1h, 3h, demain, semaine prochaine
- L'item réapparaît à l'heure choisie

### Undo (Annuler)

Après approbation, un toast apparaît :
- Cliquer "Annuler" dans les 10 secondes
- L'action est révoquée

---

## Types d'Actions

| Action | Description |
|--------|-------------|
| **Archive** | Déplacer vers le dossier **Archive** unique. Scapin utilise des métadonnées (catégories) pour le classement au lieu de dossiers imbriqués complexes. |
| **Delete** | Déplacer vers la Corbeille |
| **Reply** | Créer un brouillon de réponse |
| **Task** | Créer une tâche (OmniFocus si configuré) |
| **Flag** | Marquer comme important |
| **Forward** | Transférer à quelqu'un |

---

## Entités Extraites

Scapin identifie automatiquement :

| Type | Description | Badge |
|------|-------------|-------|
| **Personne** | Nom ou email d'un contact | 👤 bleu |
| **Date** | Échéance, rappel ou événement | 📅 orange |
| **Projet** | Nom d'un projet actif ou passé | 📁 violet |
| **Engagement** | Promesse ou action à faire | ✅ bleu |
| **Demande** | Requête formulée par l'expéditeur | 🙋 violet |
| **Décision** | Arbitrage ou choix acté | ⚖️ jaune |
| **Fait** | Information factuelle importante | 📌 gris |
| **Montant** | Prix, facture, devis | 💰 vert |
| **Événement** | Réunion, appel, rendez-vous | 🍕 rouge |
| **Lieu** | Adresse, ville, bureau | 📍 rouge |
| **Organisation** | Entreprise ou institution | 🏢 gris |
| **Logiciel** | Outil technique mentionné | 💻 bleu |
| **Lien** | URL ou ressource externe | 🔗 cyan |
| **Contact** | Coordonnées de contact | 📞 vert |

### Notes Proposées

Si une entité n'existe pas dans votre base :
- Scapin propose de créer une note
- Badge "Auto" si confiance > 90%

#### Badge "Requis"

Certains enrichissements sont marqués **Requis** (badge rouge/orange) :

| Type | Quand "Requis" ? |
|------|-----------------|
| **Deadline** | Toujours requis (information critique) |
| **Engagement** | Si importance haute ou moyenne |
| **Demande** | Si importance haute ou moyenne |
| **Décision** | Si importance haute |
| **Montant** | Si importance haute |
| **Fait** | Si importance haute |
| **Événement** | Si importance haute |

**Pourquoi c'est important ?**

Les enrichissements "Requis" contiennent des informations qui seraient **perdues** si l'email était archivé sans les extraire. Scapin garantit que :

1. Les enrichissements requis sont exécutés **avant** l'archivage
2. Si un enrichissement requis échoue, l'email reste dans le Flux (pas d'archivage)
3. Les enrichissements optionnels sont exécutés en arrière-plan (best-effort)

> **Conseil** : Si vous voyez beaucoup de badges "Requis", prenez le temps de vérifier ces enrichissements avant d'approuver.

### Tâches Proposées

Pour les emails demandant une action :
- Scapin extrait la tâche
- Propose projet et échéance

---

## Mode Focus

Pour traiter les emails en immersion :

1. Cliquer "Mode Focus" ou `/flux/focus`
2. Un email à la fois, plein écran
3. Corps complet visible
4. Actions accessibles au clavier
5. Navigation : ← →

---

## Vue Détail

Cliquer sur un item pour voir :

- Corps complet de l'email (HTML rendu)
- Historique du thread
- Pièces jointes
- Actions disponibles
- Raisonnement IA détaillé
- **Contexte utilisé** (v2.2.2+)

### Transparence du Contexte (v2.2.2)

La vue détail affiche maintenant le contexte qui a influencé l'analyse IA :

#### Influence du Contexte

Section qui explique **comment** le contexte a été utilisé :

| Champ | Description |
|-------|-------------|
| **Notes utilisées** | Liste des notes PKM consultées |
| **Explication** | Résumé de l'influence sur l'analyse |
| **Confirmations** | Informations confirmées par le contexte |
| **Contradictions** | Incohérences détectées |
| **Infos manquantes** | Données recherchées mais non trouvées |

#### Contexte Brut (collapsible)

Pour le debugging technique, une section dépliable affiche les données brutes :

- **Entités recherchées** : Personnes, projets, concepts identifiés
- **Sources consultées** : Notes, Calendrier, OmniFocus, Email
- **Notes trouvées** : Détail de chaque note avec score de pertinence
- **Événements calendrier** : Réunions et rendez-vous liés
- **Tâches OmniFocus** : Actions en cours associées

> **Conseil** : Utilisez cette section pour vérifier que Scapin consulte bien les bonnes notes et comprend correctement le contexte de vos emails

---

### Transparence de l'Analyse (v2.3)

Scapin utilise une analyse **multi-pass** qui s'adapte à la complexité de chaque email. La v2.3 vous donne une visibilité complète sur ce processus.

#### Badges de Complexité (Liste)

Dans la liste des items Flux, des badges indiquent le type d'analyse effectuée :

| Badge | Nom | Signification |
|-------|-----|---------------|
| ⚡ | Quick | Analyse rapide (1 passe, modèle léger) |
| 🔍 | Context | Contexte personnel consulté (notes, calendrier) |
| 🧠 | Complex | Escalade vers un modèle plus puissant |
| 🏆 | Opus | Modèle expert utilisé (email complexe ou à enjeux) |

> **Astuce** : Survolez la légende des badges pour voir les explications détaillées.

#### Section Analyse (Détail)

La vue détail affiche une section "🔬 Analyse" avec :

- **Nombre de passes** : Combien de fois l'IA a analysé l'email (1 à 5)
- **Modèles utilisés** : Haiku (rapide) → Sonnet (équilibré) → Opus (expert)
- **Durée totale** : Temps d'analyse
- **Badges spéciaux** :
  - `↑ Escalade` : L'IA a eu besoin d'un modèle plus puissant
  - `⚠️ High stakes` : Email détecté comme important (montant élevé, deadline proche, VIP)
- **Raison d'arrêt** : Pourquoi l'analyse s'est terminée

##### Mini-graphique de Confiance

Un petit graphique SVG montre l'évolution de la confiance de l'IA au fil des passes :
- Couleur verte = confiance élevée
- Couleur orange = confiance moyenne
- Couleur rouge = confiance faible

##### Timeline des Passes (Collapsible)

Cliquez sur "💬 X tokens (voir timeline)" pour voir le détail de chaque passe :

```
┌─ Pass 1 ───────────────────────────────────────┐
│ 🟢 Haiku  •  Extraction aveugle  •  0.8s      │
│ Confiance: 45% → 67%                           │
│                                                 │
│ 💭 Questions pour la suite:                    │
│    • "Qui est 'Marie' mentionnée ?"            │
│    • "Le 'Projet Alpha' existe-t-il ?"         │
└─────────────────────────────────────────────────┘
           │
           ▼
┌─ Pass 2 ───────────────────────────────────────┐
│ 🟠 Sonnet  •  Raffinement contextuel  •  1.2s │
│ 🔍 3 notes  •  ↑ Escalade                      │
│ Confiance: 67% → 92%                           │
└─────────────────────────────────────────────────┘
```

**Codes couleur des nœuds** :
- 🟢 Vert = Haiku (modèle rapide et économique)
- 🟠 Orange = Sonnet (modèle équilibré)
- 🔴 Rouge = Opus (modèle expert)

##### Thinking Bubbles (💭)

Quand l'IA a des doutes ou questions pendant l'analyse, elle les note pour la passe suivante. Ces "bulles de pensée" sont affichées avec le badge 💭 :

- Montre le raisonnement interne de l'IA
- Aide à comprendre pourquoi elle a escaladé
- Révèle les ambiguïtés détectées

> **Philosophie** : Montrer les doutes de l'IA renforce la confiance plus que le silence face à l'incertitude.

#### Pourquoi Pas les Autres Options ? (v2.3.1)

Quand plusieurs actions sont proposées, Scapin explique maintenant pourquoi les alternatives n'ont pas été recommandées :

- Chaque option non recommandée affiche une explication (💡)
- Une section collapsible "🤔 Pourquoi pas les autres options ?" liste toutes les alternatives rejetées

**Exemple** :
```
Archive ✓ Recommandé (92%)
  → Newsletters/Tech

Répondre (35%)
  💡 "Pas de question directe posée dans l'email"

Tâche (28%)
  💡 "Aucune action concrète demandée"
```

> **Conseil** : Utilisez cette section pour comprendre le raisonnement de Scapin et améliorer votre confiance dans ses décisions

---

## Navigation par Onglets (v2.4)

La page Péripéties utilise maintenant une navigation à 5 onglets qui reflète le cycle de vie complet des items :

| Onglet | Description | Compte |
|--------|-------------|--------|
| **À traiter** | Items analysés en attente de votre décision | Badge jaune |
| **En cours** | Items en cours d'analyse par Sancho | Badge accent |
| **Snoozés** | Items reportés (réapparaîtront plus tard) | Badge gris |
| **Historique** | Items traités (approuvés, modifiés, rejetés) | Badge gris |
| **Erreurs** | Items ayant rencontré un problème | Badge rouge |

### États du Pipeline

Chaque item passe par ces états :

```
queued → analyzing → awaiting_review → processed
                         ↓
                       error
```

### Filtres Supplémentaires

Dans chaque onglet, vous pouvez filtrer par :

- **Source** : Email, Teams, Calendrier
- **Urgence** : Urgent (rouge), Normal, Basse priorité

---

## Traitement en Lot

### Sélection Multiple

1. Cocher les items
2. Actions groupées : Approuver tout, Rejeter tout

### Raccourcis

| Touche | Action |
|--------|--------|
| `a` | Approuver sélectionné |
| `r` | Rejeter sélectionné |
| `s` | Snooze |
| `↑/↓` | Naviguer |
| `Space` | Sélectionner |

---

## Mises à jour en Temps Réel (v2.4)

Scapin utilise désormais une connexion WebSocket pour vous notifier des changements en temps réel :

### Indicateur de Connexion

Un badge **Live** (vert) ou **Déconnecté** (gris) apparaît dans l'en-tête de la page :
- **Live** : Vous recevez les mises à jour instantanément
- **Déconnecté** : Rafraîchissez manuellement pour voir les changements

### Événements Temps Réel

| Événement | Description |
|-----------|-------------|
| **Nouvel item** | Toast notification + mise à jour des compteurs |
| **Item traité** | Disparaît de la liste automatiquement |
| **Stats mises à jour** | Badges des onglets actualisés |
| **Erreur** | Notification avec possibilité de réessayer |

---

## Indicateurs Contextuels (v2.4)

Chaque péripétie affiche des indicateurs visuels pour vous aider à comprendre le contexte :

| Indicateur | Signification |
|------------|---------------|
| 📎 | Contient des pièces jointes |
| 🧠 **Contexte** | L'analyse a utilisé vos notes existantes |
| ⚡ | Analyse rapide (1 passe, haute confiance) |
| 🔍 | Contexte personnel consulté |
| 🏆 | Modèle Opus utilisé (analyse complexe) |

---

## États de Chargement (v2.4)

Scapin affiche des états visuels clairs pendant les opérations :

- **Skeleton loaders** : Cartes fantômes animées pendant le chargement initial
- **États vides personnalisés** : Messages utiles par onglet avec suggestions d'action
- **Erreurs avec Retry** : Bouton "Réessayer" en cas de problème de connexion

---

## Conseils

1. **Traitez régulièrement** — 2-3 fois par jour, 5 min chaque
2. **Faites confiance aux scores élevés** — > 85% est généralement correct
3. **Utilisez les raccourcis** — Plus rapide que la souris
4. **Vérifiez les entités** — Elles enrichissent votre base de notes
5. **Surveillez l'indicateur Live** — Assurez-vous d'être connecté pour les mises à jour temps réel
