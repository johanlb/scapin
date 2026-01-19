# Scapin — Scénarios Utilisateur

**Version**: 1.0
**Date**: 9 janvier 2026
**Statut**: En cours de rédaction

---

## Guide de Rédaction

Chaque scénario suit ce format :

```markdown
### SC-XX: [Nom court du scénario]

**Persona**: [Johan / Utilisateur mobile / Nouveau utilisateur]
**Priorité**: [CRITIQUE / HAUTE / MOYENNE / BASSE]
**Source**: [Briefing / Flux / Notes / Journal / Calendar / Teams]

**Contexte**:
> Description de la situation initiale, état du système, moment de la journée...

**Actions**:
1. L'utilisateur [action 1]
2. L'utilisateur [action 2]
3. ...

**Résultat attendu**:
- [ ] [Comportement attendu 1]
- [ ] [Comportement attendu 2]
- [ ] [Notification/feedback attendu]

**Critères de succès**:
- Temps de réponse < X secondes
- Données persistées correctement
- UI mise à jour en temps réel

**Variations**:
| Cas | Condition | Résultat différent |
|-----|-----------|-------------------|
| A | [condition] | [résultat] |
| B | [condition] | [résultat] |

**Notes techniques** (optionnel):
- API endpoints impliqués
- Composants UI concernés
- Cas limites à considérer
```

---

## Catégories de Scénarios

1. **Briefing Matinal** (SC-01 à SC-09)
2. **Traitement du Flux** (SC-10 à SC-29)
3. **Gestion des Notes** (SC-30 à SC-49)
4. **Journal Quotidien** (SC-50 à SC-59)
5. **Calendrier & Réunions** (SC-60 à SC-69)
6. **Teams & Messages** (SC-70 à SC-79)
7. **Recherche & Navigation** (SC-80 à SC-89)
8. **Configuration & Paramètres** (SC-90 à SC-99)

---

## 1. Briefing Matinal

### SC-01: Consultation du briefing matinal

**Persona**: Johan
**Priorité**: CRITIQUE
**Source**: Briefing

**Contexte**:
> Johan ouvre Scapin le matin à 8h. Il a reçu 15 emails pendant la nuit,
> a 3 réunions aujourd'hui, et 2 messages Teams non lus.

**Actions**:
1. L'utilisateur ouvre l'application (ou accède à `/`)
2. L'utilisateur consulte le briefing affiché

**Résultat attendu**:
- [ ] Section "Urgent" affiche les items prioritaires (confiance > 0.8)
- [ ] Section "Calendrier" affiche les 3 réunions du jour avec heures
- [ ] Section "À traiter" affiche le nombre d'emails en attente
- [ ] Section "Teams" affiche les 2 messages non lus
- [ ] Conflits calendrier signalés si présents

**Critères de succès**:
- Chargement < 2 secondes
- Données fraîches (< 5 min)
- Affichage responsive mobile/desktop

**Variations**:
| Cas | Condition | Résultat différent |
|-----|-----------|-------------------|
| A | Aucun item urgent | Section "Urgent" masquée ou message "RAS" |
| B | Pas de réunion | Section calendrier affiche "Journée libre" |
| C | Backend offline | Message d'erreur avec bouton retry |

---

### SC-02: Briefing pré-réunion

**Persona**: Johan
**Priorité**: HAUTE
**Source**: Briefing + Calendar

**Contexte**:
> Johan a une réunion dans 15 minutes avec Marie Dupont et Pierre Martin.
> Il veut se préparer rapidement.

**Actions**:
1. L'utilisateur clique sur l'événement calendrier dans le briefing
2. L'utilisateur consulte le briefing pré-réunion

**Résultat attendu**:
- [ ] Modal affiche les détails de la réunion (titre, heure, lieu/lien)
- [ ] Liste des participants avec contexte (derniers échanges, notes liées)
- [ ] Emails récents en rapport avec le sujet
- [ ] Points de discussion suggérés par l'IA

**Critères de succès**:
- Ouverture modal < 500ms
- Contexte participants chargé < 2s
- Suggestions pertinentes basées sur l'historique

---

## 2. Traitement du Flux

### SC-10: Approuver une action email

**Persona**: Johan
**Priorité**: CRITIQUE
**Source**: Flux

**Contexte**:
> Un email de newsletter a été analysé par Scapin avec la recommandation
> "Archiver" (confiance 0.85). Johan est d'accord.

**Actions**:
1. L'utilisateur accède à la page Flux (`/flux`)
2. L'utilisateur voit l'email avec l'action proposée
3. L'utilisateur clique sur "Approuver" (ou swipe droite sur mobile)

**Résultat attendu**:
- [ ] Email disparaît de la liste "En attente"
- [ ] Email apparaît dans "Approuvés"
- [ ] Action IMAP exécutée (email archivé côté serveur mail)
- [ ] Toast de confirmation affiché
- [ ] Bouton "Annuler" disponible pendant 15 secondes

**Critères de succès**:
- Réponse UI < 200ms (optimistic update)
- Action IMAP < 3s
- Undo fonctionnel

**Variations**:
| Cas | Condition | Résultat différent |
|-----|-----------|-------------------|
| A | Erreur IMAP | Toast erreur, email reste dans "En attente" |
| B | Clic sur Undo | Email revient dans "En attente", action annulée |

---

### SC-11: Rejeter et corriger une action

**Persona**: Johan
**Priorité**: CRITIQUE
**Source**: Flux

**Contexte**:
> Un email important a été classé "Archiver" par erreur. Johan veut le
> marquer comme tâche à faire.

**Actions**:
1. L'utilisateur clique sur "Rejeter" (ou swipe gauche)
2. L'utilisateur sélectionne la bonne action ("Créer tâche")
3. L'utilisateur valide la correction

**Résultat attendu**:
- [ ] Modal de correction s'ouvre
- [ ] Options d'action alternatives proposées
- [ ] Correction enregistrée pour apprentissage (Sganarelle)
- [ ] Nouvelle action exécutée
- [ ] Feedback utilisé pour améliorer les futures prédictions

**Critères de succès**:
- Correction prise en compte immédiatement
- Apprentissage visible dans les stats (calibration améliorée)

---

### SC-12: Reporter un email (snooze)

**Persona**: Johan
**Priorité**: MOYENNE
**Source**: Flux

**Contexte**:
> Johan reçoit un email qu'il ne peut pas traiter maintenant mais qu'il
> ne veut pas oublier.

**Actions**:
1. L'utilisateur clique sur "Reporter"
2. L'utilisateur choisit une durée (1h, 3h, demain matin, lundi)
3. L'utilisateur confirme

**Résultat attendu**:
- [ ] Email disparaît de la liste active
- [ ] Email réapparaît au moment choisi
- [ ] Notification envoyée au moment du rappel

**Critères de succès**:
- Snooze persisté (survit au redémarrage)
- Rappel précis (±1 minute)

---

### SC-13: Consulter le détail d'un email

**Persona**: Johan
**Priorité**: HAUTE
**Source**: Flux

**Contexte**:
> Johan veut lire le contenu complet d'un email avant de décider.

**Actions**:
1. L'utilisateur clique sur un email dans la liste
2. L'utilisateur consulte le détail

**Résultat attendu**:
- [ ] Page détail affiche : expéditeur, date, sujet, corps complet
- [ ] Pièces jointes listées (si présentes)
- [ ] Entités extraites affichées (personnes, dates, projets)
- [ ] Notes proposées affichées
- [ ] Historique de la conversation (si thread)

---

### SC-14: Traitement automatique des emails en background

**Persona**: Johan
**Priorité**: CRITIQUE
**Source**: Flux (Background)

**Contexte**:
> Johan ouvre Scapin le matin. Le système démarre automatiquement le traitement
> des emails en arrière-plan. Il y a 45 emails non lus dans sa boîte de réception.

**Comportement système** (automatique):
1. Au lancement de l'app, le système récupère un batch de 20 emails
2. Chaque email est analysé par l'IA (extraction entités, classification, action proposée)
3. Pour chaque email analysé :
   - Si confiance ≥ seuil configuré → **Auto-exécution** de l'action
   - Si confiance < seuil configuré → Ajout à la queue "À votre attention"
4. Quand le batch est traité, si queue < 30 items → fetch du batch suivant
5. Polling toutes les 5 minutes pour nouveaux emails
6. Polling suspendu si queue ≥ 30 items

**Résultat attendu**:
- [ ] Traitement en background sans bloquer l'UI
- [ ] Toast discret pour les actions auto-exécutées (ex: "3 emails archivés automatiquement")
- [ ] Compteur mis à jour en temps réel (badge sur onglet "À votre attention")
- [ ] Emails analysés prêts pour revue rapide (pas d'attente d'analyse)
- [ ] Actions auto-exécutées visibles dans "Traités" avec filtre

**Critères de succès**:
- Analyse < 3s par email
- UI reste responsive (pas de freeze)
- Pas de perte d'email (tous traités ou en queue)
- Polling automatique respecte l'intervalle de 5 min

**Variations**:
| Cas | Condition | Résultat différent |
|-----|-----------|-------------------|
| A | Queue atteint 30 items | Polling suspendu, message "Queue pleine" |
| B | Erreur IMAP pendant fetch | Retry automatique, puis onglet "En erreur" |
| C | Aucun nouvel email | Toast "Boîte à jour", polling continue |
| D | App en arrière-plan (mobile) | Traitement continue si autorisé par OS |

**Notes techniques**:
- Config: `PROCESSING__AUTO_EXECUTE_THRESHOLD` (0.0-1.0, défaut: 0.85)
- Config: `PROCESSING__POLLING_INTERVAL_SECONDS` (défaut: 300)
- Config: `PROCESSING__MAX_QUEUE_SIZE` (défaut: 30)
- Config: `PROCESSING__BATCH_SIZE` (défaut: 20)
- API: `POST /api/email/process` (déclenche batch)
- API: `GET /api/queue/stats` (compteurs par statut)
- WebSocket: événements `email.processed`, `email.auto_executed`, `queue.full`

---

### SC-15: Consulter les actions auto-exécutées

**Persona**: Johan
**Priorité**: HAUTE
**Source**: Flux

**Contexte**:
> Johan veut vérifier ce que Scapin a fait automatiquement pendant qu'il
> n'était pas devant l'écran.

**Actions**:
1. L'utilisateur accède à la page Flux (`/flux`)
2. L'utilisateur clique sur l'onglet "Traités"
3. L'utilisateur utilise le filtre "Auto-exécutés seulement"

**Résultat attendu**:
- [ ] Liste des emails traités automatiquement affichée
- [ ] Pour chaque item : sujet, action exécutée, % de confiance, date/heure
- [ ] Filtre fonctionnel : Tous / Auto-exécutés / Avec validation utilisateur
- [ ] Badge indiquant "Auto" sur les items auto-exécutés
- [ ] Possibilité de voir le détail de l'analyse IA

**Critères de succès**:
- Chargement liste < 1s
- Filtres appliqués instantanément (client-side)
- Historique conservé 30 jours minimum

**Notes techniques**:
- API: `GET /api/queue?status=completed&execution_type=auto`
- Champ `execution_type`: `auto` | `user_approved` | `user_modified`
- Champ `confidence_score`: float 0.0-1.0

---

### SC-16: Gérer les emails en erreur

**Persona**: Johan
**Priorité**: HAUTE
**Source**: Flux

**Contexte**:
> Une action auto-exécutée a échoué (serveur IMAP indisponible temporairement).
> L'email est dans l'onglet "En erreur".

**Actions**:
1. L'utilisateur voit le badge rouge sur l'onglet "En erreur"
2. L'utilisateur clique sur l'onglet "En erreur"
3. L'utilisateur voit l'email avec le message d'erreur
4. L'utilisateur clique sur "Réessayer"

**Résultat attendu**:
- [ ] Onglet "En erreur" visible avec compteur (badge rouge)
- [ ] Message d'erreur explicite (ex: "Connexion IMAP échouée")
- [ ] Date/heure de la dernière tentative affichée
- [ ] Nombre de tentatives affiché
- [ ] Bouton "Réessayer" pour relancer l'action
- [ ] Bouton "Ignorer" pour retirer de la liste
- [ ] Bouton "Traiter manuellement" pour envoyer vers "À votre attention"

**Critères de succès**:
- Retry automatique 3 fois avec backoff exponentiel avant d'afficher en erreur
- Erreur affichée seulement après échec des retries

**Variations**:
| Cas | Condition | Résultat différent |
|-----|-----------|-------------------|
| A | Retry réussit | Email déplacé vers "Traités", toast succès |
| B | Erreur persistante | Reste dans "En erreur", suggestion "Traiter manuellement" |

**Notes techniques**:
- API: `GET /api/queue?status=error`
- API: `POST /api/queue/{id}/retry`
- API: `POST /api/queue/{id}/dismiss`
- API: `POST /api/queue/{id}/move-to-review`
- Retry policy: 3 tentatives, backoff 5s → 30s → 120s

---

### SC-17: Configurer le seuil d'auto-exécution

**Persona**: Johan
**Priorité**: MOYENNE
**Source**: Settings

**Contexte**:
> Johan trouve que Scapin auto-exécute trop d'actions et veut augmenter
> le seuil de confiance requis.

**Actions**:
1. L'utilisateur accède à `/settings`
2. L'utilisateur trouve la section "Traitement automatique"
3. L'utilisateur ajuste le slider "Seuil de confiance" (ex: 85% → 95%)
4. L'utilisateur sauvegarde

**Résultat attendu**:
- [ ] Slider de 0% à 100% avec valeur actuelle affichée
- [ ] Explication claire du paramètre ("% de certitude requis pour action automatique")
- [ ] Prévisualisation de l'impact (ex: "Avec ce seuil, ~30% des emails seront auto-traités")
- [ ] Sauvegarde immédiate (pas de bouton "Sauvegarder" nécessaire)
- [ ] Toast de confirmation

**Critères de succès**:
- Changement appliqué immédiatement aux prochains emails
- Valeur persistée (survit au redémarrage)

**Notes techniques**:
- Config: `PROCESSING__AUTO_EXECUTE_THRESHOLD`
- API: `PUT /api/settings/processing`
- Valeurs suggérées : 70% (agressif), 85% (équilibré), 95% (prudent)

---

### SC-18: Ré-analyser un email en attente de revue

**Persona**: Johan
**Priorité**: MOYENNE
**Source**: Flux

**Contexte**:
> Johan consulte ses emails en attente de revue. Depuis l'analyse initiale,
> il a corrigé plusieurs décisions de Scapin. Il pense que l'IA a appris
> de ces corrections et pourrait maintenant proposer une meilleure action.

**Actions**:
1. L'utilisateur accède à la page Flux (`/flux`)
2. L'utilisateur consulte l'onglet "À votre attention"
3. L'utilisateur clique sur le bouton "Ré-analyser" d'un item
4. L'utilisateur attend la nouvelle analyse

**Résultat attendu**:
- [ ] Bouton "Ré-analyser" visible sur chaque item (action statique)
- [ ] Indicateur de chargement pendant la ré-analyse
- [ ] Nouvelle action proposée avec nouveau score de confiance
- [ ] Item reste dans la liste de revue (pas d'auto-exécution)
- [ ] Ancienne analyse remplacée par la nouvelle

**Critères de succès**:
- Ré-analyse < 5 secondes
- Pas d'auto-exécution même si confiance dépasse le seuil
- Item reste dans la queue de revue

**Variations**:
| Cas | Condition | Résultat différent |
|-----|-----------|-------------------|
| A | Même résultat qu'avant | Affichage mis à jour silencieusement |
| B | Action différente proposée | Nouvelle action affichée avec nouveau % |
| C | Erreur pendant analyse | Toast erreur, analyse précédente conservée |

**Notes techniques**:
- API: `POST /api/queue/{id}/reanalyze`
- Pas de limite sur le nombre de ré-analyses
- Pas d'indicateur spécial pour items ré-analysés
- Pas d'auto-exécution après ré-analyse (toujours revue manuelle)

---

### SC-19: Modifier le dossier de classement proposé

**Persona**: Johan
**Priorité**: HAUTE
**Source**: Flux

**Contexte**:
> Johan consulte un email en attente de revue. Scapin propose l'action
> "Archiver dans Archive/2025/Personnel" mais Johan préfère le classer
> dans "Archive/2025/Travail/Projets/Alpha".

**Actions**:
1. L'utilisateur voit l'action proposée avec le dossier de destination
2. L'utilisateur clique sur le chemin du dossier (zone cliquable)
3. Un champ de recherche/autocomplete s'ouvre
4. L'utilisateur tape le début du nom du dossier souhaité
5. L'utilisateur sélectionne le dossier dans les suggestions
6. L'utilisateur valide (ou le dossier est auto-sélectionné)

**Résultat attendu**:
- [ ] Chemin complet du dossier affiché (ex: `Archive/2025/Travail/Projets`)
- [ ] Zone cliquable clairement identifiable (cursor pointer, hover state)
- [ ] Champ autocomplete avec recherche fuzzy sur les noms de dossiers
- [ ] Suggestions affichent le chemin complet
- [ ] Possibilité de créer un nouveau dossier si inexistant
- [ ] Modification enregistrée comme feedback pour apprentissage (Sganarelle)
- [ ] Action mise à jour avec le nouveau dossier

**Critères de succès**:
- Recherche autocomplete < 200ms
- Maximum 10 suggestions affichées
- Création de dossier intuitive (bouton "Créer" ou entrée libre)

**Variations**:
| Cas | Condition | Résultat différent |
|-----|-----------|-------------------|
| A | Dossier inexistant tapé | Option "Créer [nom]" proposée |
| B | Aucun résultat de recherche | Message "Aucun dossier trouvé" + option créer |
| C | Clic hors du champ | Fermeture sans modification |
| D | Touche Escape | Annulation, retour au dossier original |

**Notes techniques**:
- API: `GET /api/folders/search?q={query}` (autocomplete)
- API: `POST /api/folders` (création)
- API: `PATCH /api/queue/{id}` avec `{ destination: "nouveau/chemin" }`
- Feedback Sganarelle: `folder_correction` avec `original` et `corrected`
- Composant: `FolderPicker.svelte` (autocomplete + create)

---

### SC-20: Auto-fetch intelligent des sources

**Persona**: Johan
**Priorité**: HAUTE
**Source**: Flux (Background)

**Contexte**:
> Johan utilise Scapin régulièrement. Il ne veut pas avoir à cliquer sur
> "Récupérer les emails" manuellement. Le système doit maintenir une queue
> de travail suffisante automatiquement.

**Comportement système** (automatique):

1. **Au démarrage du backend** :
   - Si `queue.count < 20` → Fetch automatique de toutes les sources actives
   - Si `queue.count >= 20` → Pas de fetch (assez de travail en attente)

2. **Pendant l'exécution** :
   - Quand `queue.count < 5` → Déclencher fetch des sources éligibles
   - Respecter le cooldown par source (éviter de re-fetch trop vite)

3. **Par source** (configurable) :
   - Email: cooldown 2 minutes (défaut)
   - Teams: cooldown 2 minutes (défaut)
   - Calendar: cooldown 5 minutes (défaut)

**Résultat attendu**:
- [ ] Fetch automatique au démarrage si queue < 20 items
- [ ] Fetch automatique quand queue descend sous 5 items
- [ ] Cooldown respecté par source (pas de fetch si dernier fetch < cooldown)
- [ ] Indicateur de sync animé dans le header pendant le fetch
- [ ] Toast discret "3 nouveaux emails ajoutés à la file"
- [ ] Compteurs mis à jour en temps réel via WebSocket

**Critères de succès**:
- Délai entre queue vide et nouveau fetch < cooldown + 10s
- Pas de fetch redondant (respecte les cooldowns)
- UI réactive (indicateur visible immédiatement)
- Configuration persistée

**Variations**:
| Cas | Condition | Résultat différent |
|-----|-----------|-------------------|
| A | Source désactivée | Pas de fetch pour cette source |
| B | Erreur de fetch | Toast erreur, retry après cooldown |
| C | Aucun nouvel email | Toast "Boîte à jour", cooldown reset |
| D | Queue atteint max (20) | Auto-fetch suspendu |

**Notes techniques**:
- Config (Settings avancés):
  ```yaml
  auto_fetch:
    enabled: true
    low_threshold: 5        # Seuil pour déclencher un fetch
    max_threshold: 20       # Seuil pour bloquer le fetch au démarrage
    sources:
      email:
        enabled: true
        cooldown_minutes: 2
      teams:
        enabled: true
        cooldown_minutes: 2
      calendar:
        enabled: true
        cooldown_minutes: 5
  ```
- API: `GET /api/queue/stats` (vérifier compteurs)
- API: `POST /api/email/process`, `POST /api/teams/poll`, `POST /api/calendar/poll`
- WebSocket événements:
  - `fetch_started` `{ source: "email" }`
  - `fetch_completed` `{ source: "email", count: 3 }`
  - `queue_updated` `{ pending: 12, processed: 45 }`
- Backend: `AutoFetchManager` singleton avec `last_fetch: Dict[source, datetime]`
- Trigger: Event-driven (après approve/reject) + polling de sécurité (toutes les 30s)

---

### SC-21: Performance du fetch et mise à jour temps réel

**Persona**: Johan
**Priorité**: CRITIQUE
**Source**: Flux

**Contexte**:
> Johan clique sur "Récupérer les emails". Le traitement semble très long
> (plusieurs minutes). De plus, une fois terminé, la page reste vide et
> Johan doit rafraîchir manuellement pour voir les nouveaux éléments.

**Problèmes identifiés**:

1. **Performance lente** : Le fetch + analyse prend trop de temps
   - Récupération IMAP ?
   - Analyse IA par email ?
   - Traitement séquentiel vs parallèle ?

2. **UI non réactive** : Pas de mise à jour automatique après fetch
   - Pas de notification WebSocket
   - Compteurs statiques
   - Utilisateur doit rafraîchir manuellement

**Résultat attendu**:

1. **Performance** :
   - [ ] Fetch IMAP < 5s pour 20 emails
   - [ ] Analyse IA en parallèle (batch de 5 emails simultanés)
   - [ ] Affichage progressif des résultats (streaming)
   - [ ] Indicateur de progression visible (X/20 analysés)

2. **Mise à jour temps réel** :
   - [ ] WebSocket événement `item_added` pour chaque nouvel élément
   - [ ] Compteurs mis à jour automatiquement sans refresh
   - [ ] Liste se met à jour dynamiquement
   - [ ] Toast "5 nouveaux éléments ajoutés"

**Critères de succès**:
- Temps total fetch + analyse < 30s pour 20 emails
- UI mise à jour en temps réel (< 1s après traitement)
- Aucun refresh manuel nécessaire

**Pistes d'amélioration**:

| Composant | Problème potentiel | Solution proposée |
|-----------|-------------------|-------------------|
| **IMAP** | Connexion lente, fetch séquentiel | Connection pooling, fetch batch |
| **AI Analysis** | Séquentiel, 3-5s par email | Parallélisation (asyncio.gather) |
| **Database** | Insertions une par une | Batch insert |
| **WebSocket** | Non utilisé pour updates | Émettre events en temps réel |
| **UI** | Polling absent | Écouter WebSocket + auto-refresh |

**Architecture cible**:
```
┌─────────────────────────────────────────────────────────────┐
│  POST /api/email/process                                    │
│    ↓                                                        │
│  1. Fetch IMAP (batch de 20)           → WS: fetch_started  │
│    ↓                                                        │
│  2. Pour chaque email (parallèle x5):                       │
│     - Analyse IA                                            │
│     - Insert DB                        → WS: item_added     │
│     - Update compteurs                 → WS: queue_updated  │
│    ↓                                                        │
│  3. Fin                                → WS: fetch_completed│
└─────────────────────────────────────────────────────────────┘

Frontend:
┌─────────────────────────────────────────────────────────────┐
│  WebSocket listener                                         │
│    - item_added → Ajouter à la liste (optimistic)           │
│    - queue_updated → Mettre à jour compteurs                │
│    - fetch_completed → Toast "X nouveaux éléments"          │
└─────────────────────────────────────────────────────────────┘
```

**Notes techniques**:
- Mesurer temps par étape avec logging détaillé
- Profiler avec `cProfile` ou `py-spy`
- Implémenter `asyncio.gather()` pour parallélisation AI
- Ajouter WebSocket events dans `src/frontin/api/websocket/`
- Frontend: écouter events dans `flux/+page.svelte`

---

## 3. Gestion des Notes

### SC-30: Consulter l'arbre des notes

**Persona**: Johan
**Priorité**: HAUTE
**Source**: Notes

**Contexte**:
> Johan veut retrouver une note sur un projet.

**Actions**:
1. L'utilisateur accède à `/notes`
2. L'utilisateur navigue dans l'arbre de dossiers
3. L'utilisateur sélectionne une note

**Résultat attendu**:
- [ ] Arbre de dossiers affiché (colonne gauche)
- [ ] Liste des notes du dossier sélectionné (colonne centrale)
- [ ] Contenu de la note sélectionnée (colonne droite)
- [ ] Métadonnées SM-2 affichées (prochaine révision, easiness factor)

---

### SC-31: Créer une nouvelle note

**Persona**: Johan
**Priorité**: HAUTE
**Source**: Notes

**Contexte**:
> Johan veut créer une note sur une nouvelle personne rencontrée.

**Actions**:
1. L'utilisateur clique sur "Nouvelle note"
2. L'utilisateur choisit le type (Personne)
3. L'utilisateur remplit le contenu
4. L'utilisateur sauvegarde

**Résultat attendu**:
- [ ] Éditeur Markdown ouvert
- [ ] Template de note "Personne" pré-rempli
- [ ] Auto-save actif (indicateur visible)
- [ ] Note commitée dans Git automatiquement

---

### SC-32: Session de révision SM-2

**Persona**: Johan
**Priorité**: HAUTE
**Source**: Notes

**Contexte**:
> 5 notes sont dues pour révision aujourd'hui.

**Actions**:
1. L'utilisateur clique sur "Réviser" depuis le dashboard
2. L'utilisateur évalue chaque note (0-5)
3. L'utilisateur termine la session

**Résultat attendu**:
- [ ] Mode focus pleine page
- [ ] Notes présentées une par une
- [ ] Boutons d'évaluation 0-5 avec raccourcis clavier
- [ ] Progression affichée (2/5, 3/5...)
- [ ] Intervalles recalculés selon SM-2
- [ ] Statistiques de session à la fin

---

### SC-33: Synchroniser Apple Notes

**Persona**: Johan
**Priorité**: MOYENNE
**Source**: Notes

**Contexte**:
> Johan a créé des notes dans Apple Notes qu'il veut importer.

**Actions**:
1. L'utilisateur clique sur "Sync Apple Notes"
2. L'utilisateur attend la synchronisation

**Résultat attendu**:
- [ ] Indicateur de progression affiché
- [ ] Notes importées en Markdown
- [ ] Dossiers Apple Notes reproduits
- [ ] Compteur de notes synchronisées affiché

---

## 4. Journal Quotidien

### SC-50: Compléter le journal du soir

**Persona**: Johan
**Priorité**: HAUTE
**Source**: Journal

**Contexte**:
> En fin de journée, Johan veut faire son journaling quotidien.

**Actions**:
1. L'utilisateur accède à `/journal`
2. L'utilisateur répond aux questions générées
3. L'utilisateur corrige les décisions de Scapin si nécessaire
4. L'utilisateur valide

**Résultat attendu**:
- [ ] Questions personnalisées basées sur la journée
- [ ] Résumé des actions Scapin du jour
- [ ] Possibilité de corriger les mauvaises décisions
- [ ] Feedback enregistré pour calibration

---

## 5. Calendrier & Réunions

### SC-60: Voir les événements du jour

**Persona**: Johan
**Priorité**: HAUTE
**Source**: Calendar

**Contexte**:
> Johan veut voir son planning de la journée.

**Actions**:
1. L'utilisateur consulte le briefing ou la page calendrier

**Résultat attendu**:
- [ ] Liste des événements avec heures
- [ ] Conflits signalés visuellement (badge orange)
- [ ] Bouton briefing pré-réunion sur chaque événement

---

## 6. Teams & Messages

### SC-70: Répondre à un message Teams urgent

**Persona**: Johan
**Priorité**: MOYENNE
**Source**: Teams

**Contexte**:
> Un collègue a envoyé un message important sur Teams.

**Actions**:
1. L'utilisateur voit la notification dans le briefing
2. L'utilisateur clique pour voir le détail
3. L'utilisateur répond directement depuis Scapin

**Résultat attendu**:
- [ ] Message affiché avec contexte de la conversation
- [ ] Champ de réponse disponible
- [ ] Réponse envoyée via Graph API
- [ ] Confirmation de l'envoi

---

## 7. Recherche & Navigation

### SC-80: Recherche globale (Cmd+K)

**Persona**: Johan
**Priorité**: HAUTE
**Source**: Global

**Contexte**:
> Johan cherche quelque chose mais ne sait pas où c'est.

**Actions**:
1. L'utilisateur appuie sur Cmd+K (ou Ctrl+K)
2. L'utilisateur tape sa recherche
3. L'utilisateur sélectionne un résultat

**Résultat attendu**:
- [ ] Palette de commande ouverte
- [ ] Résultats groupés par type (notes, emails, événements)
- [ ] Navigation clavier fonctionnelle
- [ ] Résultat ouvre la bonne page

---

## 8. Configuration & Paramètres

### SC-90: Configurer une intégration

**Persona**: Johan
**Priorité**: BASSE
**Source**: Settings

**Contexte**:
> Johan veut activer l'intégration Microsoft Teams.

**Actions**:
1. L'utilisateur accède à `/settings`
2. L'utilisateur clique sur "Microsoft Teams"
3. L'utilisateur suit le flux d'authentification OAuth

**Résultat attendu**:
- [ ] Instructions claires affichées
- [ ] Redirection vers Microsoft login
- [ ] Token stocké de manière sécurisée
- [ ] Statut "Connecté" affiché après succès

---

## Template Vide (à copier)

### SC-XX: [Titre du scénario]

**Persona**: Johan
**Priorité**: [CRITIQUE / HAUTE / MOYENNE / BASSE]
**Source**: [Briefing / Flux / Notes / Journal / Calendar / Teams / Settings]

**Contexte**:
> [Description de la situation initiale]

**Actions**:
1. L'utilisateur [action]
2. L'utilisateur [action]

**Résultat attendu**:
- [ ] [Comportement 1]
- [ ] [Comportement 2]

**Critères de succès**:
- [Critère mesurable]

**Variations**:
| Cas | Condition | Résultat différent |
|-----|-----------|-------------------|
| A | [condition] | [résultat] |

---

## Mapping Scénarios → Tests

| Scénario | Test E2E | Test API | Test Unit |
|----------|----------|----------|-----------|
| SC-01 | `briefing.spec.ts` | `test_briefing_api.py` | - |
| SC-10 | `flux.spec.ts` | `test_queue_api.py` | - |
| SC-14 | `flux-background.spec.ts` | `test_background_processing.py` | `test_email_processor.py` |
| SC-15 | `flux.spec.ts` | `test_queue_api.py` | - |
| SC-16 | `flux-errors.spec.ts` | `test_queue_errors.py` | - |
| SC-17 | `settings.spec.ts` | `test_settings_api.py` | - |
| SC-18 | `flux-reanalyze.spec.ts` | `test_reanalyze_api.py` | - |
| SC-19 | `flux-folder-picker.spec.ts` | `test_folder_picker_api.py` | - |
| SC-20 | `flux-autofetch.spec.ts` | `test_autofetch_api.py` | `test_autofetch_manager.py` |
| SC-21 | `flux-performance.spec.ts` | `test_flux_performance.py` | `test_email_processor_perf.py` |
| SC-30 | `notes.spec.ts` | `test_notes_api.py` | - |
| SC-50 | `journal.spec.ts` | `test_journal_api.py` | - |
| SC-80 | `search.spec.ts` | `test_search_api.py` | - |

---

*Document créé le 9 janvier 2026*
