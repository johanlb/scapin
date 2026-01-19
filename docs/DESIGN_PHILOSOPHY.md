# Scapin — Philosophie de Conception

**Version** : 1.1  
**Date** : 2 janvier 2026  
**Auteur** : Johan Le Bail, en collaboration avec Claude  
**Statut** : Document Fondateur — Référence pour toutes les décisions de conception

---

## Préambule

Ce document capture les principes philosophiques et cognitifs qui guident la conception de Scapin. Il ne s'agit pas d'une spécification technique (voir ARCHITECTURE.md pour cela), mais du **pourquoi** derrière chaque décision. C'est le document de référence pour comprendre l'âme de Scapin et prendre des décisions cohérentes lors du développement.

**Audience** : Johan (pour relecture et validation), Claude Code (pour guider le développement), futurs contributeurs (pour comprendre la vision).

---

## Table des Matières

1. [Vision Fondamentale](#1-vision-fondamentale)
2. [Fondements Théoriques](#2-fondements-théoriques)
3. [Philosophie du Partenariat Cognitif](#3-philosophie-du-partenariat-cognitif)
4. [Principes de Conception](#4-principes-de-conception)
5. [Architecture de l'Information](#5-architecture-de-linformation)
6. [Modèle de Confiance et d'Autonomie](#6-modèle-de-confiance-et-dautonomie)
7. [Stratégie d'Intégration](#7-stratégie-dintégration)
8. [Boucle d'Amélioration Continue](#8-boucle-damélioration-continue)
9. [Rythme Quotidien](#9-rythme-quotidien)
10. [Scalabilité et Multi-Instances](#10-scalabilité-et-multi-instances)
11. [Mesures de Succès](#11-mesures-de-succès)
12. [Anti-Patterns à Éviter](#12-anti-patterns-à-éviter)
13. [Références Théoriques](#13-références-théoriques)

---

## 1. Vision Fondamentale

### La Mission de Scapin

> **"Prendre soin de Johan mieux que Johan lui-même."**

Scapin n'est pas un simple assistant qui attend des ordres. C'est un **gardien cognitif proactif** inspiré du valet de comédie de Molière : rusé, anticipant les besoins de son maître, parfois même désobéissant intelligemment pour son bien.

### Ce que Scapin doit être

- **Une extension cognitive active** — Scapin enrichit, prépare, facilite, pense le plus loin possible
- **Un partenaire qui anticipe** — Brouillons de réponse prêts, contexte rappelé, options analysées
- **Un challenger bienveillant** — Meilleur que Johan sur la cohérence et la continuité
- **Un gardien de la mémoire** — Qui se souvient de ce que Johan oublie
- **Un réducteur de friction** — Qui fait que la délégation coûte moins cher que l'exécution

### Ce que Scapin ne doit pas être

- Un simple automatiseur de tâches répétitives
- Un outil passif qui attend des instructions explicites
- Un système qui augmente la charge mentale au lieu de la réduire
- Un substitut aux relations humaines

---

## 2. Fondements Théoriques

### 2.1 Extended Mind Thesis (Clark & Chalmers, 1998)

**Principe** : Les processus cognitifs ne sont pas confinés au cerveau. L'environnement peut jouer un rôle actif constitutif de la cognition.

**Exemple fondateur** : Otto (atteint d'Alzheimer) et son carnet vs Inga et sa mémoire biologique. Les deux "se souviennent" de la même manière fonctionnelle — le carnet d'Otto EST une partie de sa mémoire.

**Implication pour Scapin** : Scapin n'est pas un outil externe, mais une **extension de l'esprit de Johan**. Les fiches, les contextes, les décisions stockées font partie de sa cognition étendue.

**Critère de "parité fonctionnelle"** (révisé vers "complémentarité") : Si Scapin remplit un rôle que la mémoire biologique remplirait autrement, et s'il est accessible de manière fiable, alors il fait partie du système cognitif.

### 2.2 Mémoire Transactive (Wegner, 1985)

**Principe** : Dans les couples et les groupes, un système de mémoire partagée émerge où les membres se spécialisent et savent "qui sait quoi".

**Trois processus clés** :
1. **Encodage** — Qui va stocker cette information ?
2. **Stockage** — Chacun développe une expertise
3. **Récupération** — Savoir à qui demander

**Implication pour Scapin** : Le duo Johan + Scapin forme un système de mémoire transactive. Johan sait que Scapin "sait" certaines choses (contacts, historiques, décisions passées) et peut lui demander au lieu de mémoriser.

**Extension future** : Johan + Scapin-Johan + Damien + Scapin-Damien = mémoire transactive distribuée à 4 nœuds.

### 2.3 Effet Google (Sparrow, Liu & Wegner, 2011)

**Découverte** : Quand les gens savent qu'ils auront accès futur à une information, ils retiennent moins l'information elle-même mais mieux sa localisation.

**Paradoxe** : Cette stratégie est cognitivement efficace (délégation) mais peut créer une dépendance et un appauvrissement de la mémoire interne.

**Implication pour Scapin** : 
- C'est normal et souhaitable que Johan ne mémorise pas tout ce qui est dans Scapin
- Scapin doit être **fiable** (l'information sera là quand demandée)
- Scapin doit aider à **retrouver** efficacement (méta-mémoire : savoir où chercher)
- Certaines informations doivent être **activement révisées** pour rester en mémoire biologique

### 2.4 Pharmacologie de Stiegler

**Concept central** : Le *pharmakon* — tout système technique est simultanément poison ET remède. L'écriture (selon Platon/Stiegler) peut détruire la mémoire (hypomnèse qui remplace l'anamnèse) ou la renforcer.

**La question critique** : Comment faire pour que l'externalisation soit un remède plutôt qu'un poison ?

**Réponse de Stiegler** : "Produire du savoir avec" — L'outil technique ne doit pas court-circuiter la pensée mais l'augmenter.

**Implication pour Scapin** :

| Risque (Poison) | Solution (Remède) |
|-----------------|-------------------|
| Court-circuit : Scapin pense à la place de Johan | Scapin propose, Johan décide. Débat et challenge encouragés |
| Appauvrissement : Johan ne retient plus rien | Révision espacée pour les informations critiques |
| Dépendance : Paralysie sans Scapin | Scapin enrichit les capacités, ne les remplace pas |
| Passivité : Johan devient consommateur | Journaling actif, génération de savoir, connexions créatives |

### 2.5 Rétentions Tertiaires (Stiegler)

**Concept** : Les rétentions tertiaires sont les traces techniques qui permettent d'accéder à un passé non vécu personnellement. Elles constituent la mémoire collective et individuelle externalisée.

**Implication pour Scapin** : 
- Emails → traces structurées (fiches, résumés)
- Décisions → traces de pensée (pourquoi, alternatives écartées)
- Relations → condensations (fiches personnes avec profil relationnel)

Les rétentions tertiaires de Scapin doivent être suffisamment riches pour **reconstituer le contexte** même des mois plus tard.

---

## 3. Philosophie du Partenariat Cognitif

### 3.1 Nature du Partenariat

Scapin est une **extension active indispensable**, pas un outil passif. La métaphore du valet de comédie est essentielle :

| Caractéristique | Manifestation |
|-----------------|---------------|
| **Anticipation** | Brouillons de réponse prêts, contexte rappelé avant une rencontre |
| **Initiative** | Suggère des actions, rappelle des oublis (anniversaires, deadlines) |
| **Intelligence** | Analyse les options, explique les alternatives écartées |
| **Fidélité** | Connaissance intime, aucun sujet tabou, confiance totale |
| **Challenge** | Veille à la cohérence, signale les contradictions |

### 3.2 Ce que Johan délègue à Scapin

**Délégation complète (Scapin "sait", Johan "retrouve")** :
- Dates précises (anniversaires, échéances contractuelles)
- Coordonnées de contact
- Historique des échanges avec une personne
- Décisions passées et leur rationale
- Détails factuels de projets

**Connaissance active (Johan doit pouvoir mobiliser)** :
- Stratégies en cours
- Relations clés et leur dynamique
- Grandes lignes des projets importants
- Préférences et styles de communication des personnes proches

**Sagesse intériorisée (révision espacée recommandée)** :
- Visages des personnes (éviter les situations gênantes)
- Principes de décision personnels
- Valeurs et objectifs de vie

### 3.3 Tension Centrale Résolue

> **Paradoxe** : Johan a besoin de déléguer massivement (trop de choses à gérer) ET de préserver sa capacité à penser (débat, challenge, exploration).

**Résolution** : Scapin est simultanément :
- **Déchargeur cognitif** — Pour les micro-tâches et le contexte factuel
- **Sparring partner intellectuel** — Pour le débat, l'exploration, le challenge des idées

Ces deux rôles ne sont pas contradictoires mais complémentaires. Scapin libère de la bande passante cognitive pour que Johan puisse penser aux choses importantes.

---

## 4. Principes de Conception

### 4.1 Qualité sur Vitesse

> "Un assistant qui prend 15 secondes mais fait le BON choix est infiniment meilleur qu'un qui est instantané mais se trompe."

**Temps de raisonnement acceptable** : 10-20 secondes pour une décision de qualité.

**Rationale** : Les utilisateurs peuvent attendre pour la qualité ; ils ne peuvent pas récupérer d'une mauvaise décision.

### 4.2 Proactivité Maximale

Scapin doit :
- **Interrompre** quand c'est utile (rappels importants, contexte avant une réunion)
- **Suggérer sans qu'on demande** (pistes, alertes, opportunités)
- **Challenger même si inconfortable** (cohérence, contradictions, risques)
- **Anticiper au maximum** (brouillons prêts, scénarios préparés)

**Limite** : Pas de limite à la proactivité. Johan préfère trop d'anticipation que pas assez.

### 4.3 Intimité Totale

> "Scapin doit tout savoir. Aucune limite d'intrusion intime pour l'efficacité."

**Conséquences** :
- Aucun sujet tabou dans les échanges
- Accès complet à tous les emails, fichiers, messages
- Connaissance des relations personnelles, familiales, amicales
- Compréhension des émotions, stress, contexte personnel

**Responsabilité** : Cette intimité exige une fiabilité et une discrétion absolues.

### 4.4 Apprentissage Progressif

Au lieu de règles explicites prédéfinies, Scapin **apprend des corrections** de Johan :
- Corrections répétées → ajustement des seuils de confiance
- Patterns détectés → règles émergentes
- Feedback explicite et implicite → amélioration continue

**Prudence initiale** : Pour les actions externes (emails envoyés, etc.), Scapin commence prudent et élargit son autonomie progressivement.

### 4.5 Construction Propre dès le Début

> "Je préfère que ce soit lent mais bien construit."

**Approche** : Vision long terme, conception totale, construction parfaite et propre dès le début. Pas de dette technique acceptée, pas de raccourcis.

**Séquençage** : Les phases A (email processing) et B (journaling + feedback) sont les priorités immédiates car les plus liées et les plus impactantes pour la réduction de charge mentale.

---

## 5. Architecture de l'Information

### 5.1 Information en Couches

Toute information est structurée en trois niveaux de détail :

| Niveau | Contenu | Temps de lecture | Usage |
|--------|---------|------------------|-------|
| **Niveau 1** | Résumé actionnable | 30 secondes | Décision rapide, briefing |
| **Niveau 2** | Contexte et options | 2 minutes | Compréhension, choix informé |
| **Niveau 3** | Détails complets, alternatives écartées | Variable | Auto-alimentation Scapin, audit, apprentissage |

**Principe de présentation** : Johan consulte le niveau qu'il souhaite. Par défaut, Niveau 1. Creuser si besoin.

**Stockage** : Le Niveau 3 est toujours stocké pour permettre à Scapin de s'auto-alimenter et de retrouver le raisonnement complet.

### 5.2 Filtrage Intelligent

Scapin peut et doit filtrer intelligemment :
- **Risque faible** (newsletters, notifications) → traitement autonome
- **Risque moyen** → résumé Niveau 1 avec option de creuser
- **Risque élevé** (décisions stratégiques, relations sensibles) → présentation complète + validation

### 5.3 Création Sélective de Fiches

**Critères pour créer une fiche personne** :
- Importance de la relation (pas chaque contact occasionnel)
- Continuité probable (interactions futures attendues)
- Pertinence pour les décisions (contexte utile)

**Maintenance** :
- Revues périodiques (proposition de mise à jour)
- Dialogues audio (validation en voiture, moments libres)
- Archivage des fiches inactives (pas de suppression)

### 5.4 Métamémoire Explicite

Scapin maintient une "carte" de ce qu'il sait :
- Index des domaines d'expertise par personne
- Sources autoritatives par sujet
- Historique de qui a fourni quelle information
- Niveau de confiance par type d'information

---

## 6. Modèle de Confiance et d'Autonomie

### 6.1 Seuils de Confiance Appris

Au lieu de règles explicites, les seuils d'autonomie émergent de l'apprentissage :

```
Correction répétée sur type X → Scapin consulte avant d'agir sur X
Approbation systématique sur type Y → Scapin agit en autonomie sur Y
```

**Calibration continue** : Chaque feedback (explicite ou implicite) ajuste les seuils.

### 6.2 Modes d'Exécution

| Mode | Déclencheur | Comportement |
|------|-------------|--------------|
| **Auto** | Confiance haute + risque faible | Exécute, informe après |
| **Review** | Confiance moyenne OU risque moyen | Prépare, attend validation |
| **Manual** | Confiance basse OU risque haut | Présente options, Johan décide et exécute |

### 6.3 Prudence Externe

**Règle spéciale** : Toute action visible de l'extérieur (email envoyé, message, publication) requiert une prudence accrue :
- Phase initiale : toujours Review
- Après apprentissage : Auto seulement pour patterns très établis
- Jamais Auto pour nouveaux interlocuteurs ou sujets sensibles

---

## 7. Stratégie d'Intégration

### 7.1 Vision Unifiée des Flux Entrants

Scapin traite tous les flux de messages comme un pipeline unifié. La nature du canal (email, Teams, LinkedIn) n'est qu'un attribut du message — le traitement cognitif reste identique.

```
Flux Entrants (Trivelin)
├── Emails
│   ├── johan@eufonie.fr (professionnel)
│   └── johanlb@me.com (personnel + AWCS)
├── Messages Teams (professionnel Eufonie/Skiillz)
├── Messages LinkedIn (professionnel, priorité basse)
├── Notifications Planner (lecture seule, contexte équipe)
└── [Futur] Autres canaux (WhatsApp, SMS, etc.)
```

**Principe** : Tout message entrant = PerceivedEvent → même pipeline cognitif (Trivelin → Sancho → etc.)

### 7.2 Système de Tâches Unifié

**Décision fondamentale** : OmniFocus est le **système maître** pour les tâches de Johan. Aucun autre système ne doit fragmenter l'attention.

```
Sources de tâches (lecture)              Système maître (écriture)
├── Planner (contexte équipe Eufonie) ─┐
├── Emails (actions extraites)        ─┼──→  OmniFocus
├── Teams (actions extraites)         ─┤      (seul système de Johan)
├── LinkedIn (actions extraites)      ─┘
└── Transcriptions réunion            ─┘
```

**Planner** : Scapin lit Planner pour comprendre le contexte des projets d'équipe et les tâches assignées à d'autres, mais les tâches de Johan sont centralisées dans OmniFocus.

### 7.3 Calendrier — Modèle de Confiance Progressive

Le calendrier suit le modèle de confiance appris en trois phases :

**Phase 1 — Lecture + Suggestions** (initial)
```
Scapin : "Tu as RDV avec X demain, voici le briefing contextuel"
Scapin : "Je suggère de déplacer Y à jeudi pour éviter le conflit avec Z"
Johan : Valide ou refuse manuellement
```

**Phase 2 — Modification avec Validation**
```
Scapin : "J'ai préparé ce créneau pour la réunion budget. Je l'ajoute ?"
Johan : Oui / Non / Modifier
```

**Phase 3 — Autonomie sur Patterns Établis** (après apprentissage)
```
Scapin : Ajoute automatiquement les types de RDV dont les patterns sont validés
Scapin : Continue de demander validation pour nouveaux types
```

**Calendriers concernés** :
- iCloud Calendar (personnel + AWCS)
- Exchange Calendar (Eufonie/Skiillz)

### 7.4 Teams — Intégration Complète

**Niveau d'intégration** : Complet (lecture + réponses + appels)

| Fonction | Comportement |
|----------|--------------|
| **Lecture messages** | Intégré au flux entrant Trivelin |
| **Réponses** | Brouillons préparés, Johan valide avant envoi |
| **Appels planifiés** | Briefing contextuel avant chaque appel |
| **Planification appels** | Scapin peut proposer des créneaux et envoyer les invitations (après validation) |

### 7.5 LinkedIn — Focus Messagerie

**Périmètre actuel** : Messagerie uniquement (pas de publication de contenu).

**Traitement** : Les messages LinkedIn sont traités comme un type d'email avec une **priorité basse**. Ils passent par le même pipeline mais avec un filtrage plus agressif.

| Aspect | Décision |
|--------|----------|
| **Priorité** | Basse (beaucoup moins urgente que emails pro) |
| **Filtrage** | Plus agressif (beaucoup de spam/prospection) |
| **Réponses** | Brouillons préparés, validation requise |
| **Publication** | Hors périmètre v1.0 |

### 7.6 Autres Intégrations

| Intégration | Niveau d'accès | Phase Prévue |
|-------------|----------------|--------------|
| **Apple Notes** | Lecture + Écriture | v1.0 (MCP existant) |
| **OmniFocus** | Lecture + Écriture | v1.0 (MCP existant) |
| **OneDrive/SharePoint** | Lecture (contexte fichiers pro) | v1.2 |
| **Apple Shortcuts** | Bidirectionnel (déclencheur + receveur) | v1.1 |
| **Transcriptions réunion** | Input processing | v1.0 |

### 7.7 Priorité des Domaines

**v1.0 — Critique** :
- Réduction charge mentale professionnelle (Eufonie, Skiillz)
- Gestion AWCS (copropriété)
- Flux emails et Teams

**v1.5+ — Nice to Have** :
- Accompagnement loisirs (guitare, chant)
- Gestion vie personnelle élargie
- Publication LinkedIn

---

## 8. Boucle d'Amélioration Continue

### 8.1 Le Journaling comme Cœur du Système

Le journaling quotidien est le mécanisme central d'amélioration :

```
Journée vécue
     ↓
Scapin pré-remplit le journal (ce qu'il sait)
     ↓
Johan complète et corrige (~15 min)
     ↓
Enrichissement des fiches (personnes, projets, décisions)
     ↓
Meilleure analyse future
     ↓
Suggestions plus pertinentes
     ↓
Feedback via journaling suivant
     ↓
Amélioration du système
```

### 8.2 Timing du Journaling

**Deux moments possibles** :
- **Fin de journée** : Synthèse complète, prise de recul
- **Au fil de l'eau** : Validation post-réunion, capture à chaud

**Durée cible** : ~15 minutes par jour.

**Principe** : Scapin doit faciliter pour que ce soit rapide et efficace. Il pré-remplit, Johan ajuste.

### 8.3 Revues Périodiques

| Période | Focus | Durée |
|---------|-------|-------|
| **Quotidienne** | Journaling, micro-ajustements | 15 min |
| **Hebdomadaire** | Revue GTD, fiches à mettre à jour | 30-60 min |
| **Mensuelle** | Équilibre domaines, objectifs, système | 1-2h |
| **Trimestrielle/Semestrielle** | Vision, grands objectifs, ajustements stratégiques | 2-4h |

### 8.4 Ce que le Journaling Alimente

- **Fiches personnes** : Nouvelles interactions, changements de situation
- **Fiches projets** : Avancement, décisions, blocages
- **Patterns** : Ce qui fonctionne, ce qui ne fonctionne pas
- **Modèle de Johan** : Préférences, réactions, valeurs
- **Suggestions futures** : Connexions à faire, rappels à programmer

### 8.5 Création de Savoir

Au-delà de la capture, le système encourage la **production active de savoir** :
- Débat et challenge des idées
- Connexions entre domaines disparates
- Synthèses et frameworks personnels
- Partage des réussites et des écueils

---

## 9. Rythme Quotidien

### 9.1 Vision d'une Journée avec Scapin

| Moment | Scapin fait | Johan fait |
|--------|-------------|------------|
| **Réveil** | Briefing du jour : priorités, personnes à voir, rappels contextuels, météo décisionnelle | Consulte, ajuste si nécessaire |
| **Emails** | Pré-analyse, tri, brouillons de réponse préparés | Valide, ajuste, envoie |
| **Messages Teams** | Idem emails, intégré au flux | Valide, ajuste, envoie |
| **Avant réunion** | Briefing contextuel : historique relation, points à aborder, risques | Consulte, se prépare |
| **Avant appel Teams** | Briefing + rappel créneaux suivants | Consulte |
| **Après réunion** | Propose résumé à valider, extrait actions potentielles | Valide/enrichit à chaud |
| **Fin de journée** | Pré-remplit journal, pose questions ciblées, propose mises à jour fiches | Complète (~15 min), feedback |
| **Nuit** | Traite feedback, enrichit fiches, prépare lendemain, maintenance système | Dort sereinement |

### 9.2 Quick Wins Prioritaires

Les deux victoires rapides qui comptent le plus :
1. **Inbox Zero assisté** — Gestion des emails avec pré-analyse et brouillons
2. **Tri des données existantes** — Transformation de l'information éparpillée en fiches organisées

**Priorité compte email** : Personnel d'abord (johanlb@me.com) car moins sensible et bon terrain d'apprentissage.

---

## 10. Scalabilité et Multi-Instances

### 10.1 Architecture Moteur / Données

Scapin est conçu comme un **logiciel de mail** : le même moteur, mais chaque utilisateur a son instance personnelle avec ses données et configurations.

```
┌─────────────────────────────────────────────────────────┐
│                    MOTEUR SCAPIN                        │
│  (Code, algorithmes, modèles, logique)                  │
│  → Partageable, versionné, améliorable collectivement   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              INSTANCE PERSONNELLE                       │
│  • Configuration (API keys, préférences)                │
│  • Données (fiches, historique, patterns)               │
│  • Modèle personnel (seuils, calibration)               │
│  → Strictement privé, jamais partagé                    │
└─────────────────────────────────────────────────────────┘
```

### 10.2 Cercles de Confiance Bidimensionnels

Le partage d'information entre instances suit un modèle à deux dimensions :

**Dimension 1 : Domaine**
| Domaine | Exemples |
|---------|----------|
| **Professionnel** | Eufonie, Skiillz, clients, collaborateurs |
| **Personnel** | Famille, santé, finances personnelles |
| **AWCS** | Copropriété, conseil, résidents |

**Dimension 2 : Proximité**
| Cercle | Qui | Niveau de partage |
|--------|-----|-------------------|
| **0** | Scapin-Johan | Tout, sans exception |
| **1** | Partenaire (couple/associé) | Professionnel partagé + personnel filtré |
| **2** | Famille / Comité direction | Domaine pertinent, filtré |
| **3** | Collaborateurs / Amis | Informations de travail, contexte limité |
| **4** | Autres / Inconnus | Minimum nécessaire |

### 10.3 Communication Inter-Instances

**Vision future** : Scapin-Johan et Scapin-Damien peuvent dialoguer et se coordonner.

**Règles** :
- Un **valet filtreur** analyse chaque échange potentiel
- Jamais de partage automatique total
- En cas de conflit : les valets en réfèrent à leurs maîtres (comme dans les pièces de théâtre)

---

## 11. Mesures de Succès

### 11.1 Objectif Principal

> **Réduire la charge mentale de Johan.**

C'est le critère ultime. Tout le reste en découle.

### 11.2 Objectifs Secondaires

| Objectif | Indicateur |
|----------|------------|
| **Temps gagné** | Heures récupérées par semaine |
| **Meilleures décisions** | Moins de regrets, plus de cohérence |
| **Grands objectifs atteints** | Progression sur les projets importants |
| **Équilibre vie** | Temps travail vs loisirs vs bien-être |
| **Délégation fluide** | Coût délégation < coût exécution |

### 11.3 Signaux de Succès

- Johan ne cherche plus pendant 15 min pour une micro-tâche
- Les anniversaires ne sont plus oubliés
- Le contexte est disponible avant chaque interaction importante
- Les emails sont traités sans accumulation inbox
- Johan peut se déconnecter sereinement

### 11.4 Signaux d'Échec

- Charge mentale augmentée (trop de notifications, de choix, de validation)
- Sentiment de perte de contrôle
- Erreurs de Scapin non détectées
- Dépendance paralysante
- Appauvrissement de la réflexion personnelle

---

## 12. Anti-Patterns à Éviter

### 12.1 Court-Circuit Cognitif

**Symptôme** : Scapin décide, Johan exécute sans réfléchir.

**Garde-fou** : Maintenir le débat, le challenge, la génération active de savoir via le journaling.

### 12.2 Surcharge Informationnelle

**Symptôme** : Plus d'information présentée → plus de charge mentale.

**Garde-fou** : Information en couches, filtrage intelligent, présentation progressive.

### 12.3 Fausse Confiance

**Symptôme** : Scapin affiche 95% de confiance mais se trompe.

**Garde-fou** : Calibration continue, consensus multi-provider, humilité épistémique.

### 12.4 Dépendance Paralysante

**Symptôme** : Johan ne peut plus rien faire sans Scapin.

**Garde-fou** : Scapin enrichit les capacités, ne les remplace pas. Les compétences critiques restent exercées.

### 12.5 Érosion de la Mémoire Biologique

**Symptôme** : Johan ne retient plus rien, même l'important.

**Garde-fou** : Révision espacée pour les connaissances critiques (visages, principes, relations clés).

### 12.6 Automatisation Aveugle

**Symptôme** : Actions exécutées sans compréhension du contexte.

**Garde-fou** : Rétentions tertiaires riches (Niveau 3), trace de raisonnement toujours stockée.

### 12.7 Fragmentation des Systèmes

**Symptôme** : Tâches éparpillées entre Planner, OmniFocus, notes, etc.

**Garde-fou** : OmniFocus = système maître. Tous les autres systèmes sont des sources de lecture, pas d'écriture de tâches.

---

## 13. Références Théoriques

### Philosophie de l'Esprit

- **Clark, A. & Chalmers, D. (1998)**. "The Extended Mind." *Analysis*, 58(1), 7-19.
  - Thèse fondatrice de l'esprit étendu
  - Exemple Otto et le carnet

- **Clark, A. (2008)**. *Supersizing the Mind: Embodiment, Action, and Cognitive Extension.* Oxford University Press.
  - Développement complet de l'Extended Mind

### Psychologie Cognitive

- **Wegner, D. M. (1985)**. "Transactive Memory: A Contemporary Analysis of the Group Mind." In *Theories of Group Behavior* (pp. 185-208). Springer.
  - Théorie de la mémoire transactive dans les couples et groupes

- **Sparrow, B., Liu, J., & Wegner, D. M. (2011)**. "Google Effects on Memory: Cognitive Consequences of Having Information at Our Fingertips." *Science*, 333(6043), 776-778.
  - L'effet Google et ses implications

### Philosophie de la Technique

- **Stiegler, B. (1994-2001)**. *La technique et le temps* (3 tomes). Galilée.
  - Pharmacologie, rétentions tertiaires, anamnèse vs hypomnèse

- **Stiegler, B. (2008)**. *Prendre soin de la jeunesse et des générations.* Flammarion.
  - Application de la pharmacologie à l'éducation et aux techniques cognitives

### Personal Knowledge Management

- **Forte, T. (2022)**. *Building a Second Brain.* Atria Books.
  - Méthodologie PARA, CODE, capture progressive

- **Ahrens, S. (2017)**. *How to Take Smart Notes.* CreateSpace.
  - Méthode Zettelkasten, notes atomiques, connexions

- **Allen, D. (2001)**. *Getting Things Done.* Penguin.
  - Méthodologie GTD, horizons d'attention, revues

### Intelligence Artificielle et Raisonnement

- **Yao, S. et al. (2023)**. "ReAct: Synergizing Reasoning and Acting in Language Models."
  - Raisonnement itératif dans les LLMs

- **Wei, J. et al. (2022)**. "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models."
  - Pensée étape par étape

### Prise de Décision

- **Boyd, J. (1976)**. "The OODA Loop."
  - Observe, Orient, Decide, Act — cycle décisionnel

- **Klein, G. (1993)**. "Recognition-Primed Decision Model."
  - Décision intuitive des experts basée sur la reconnaissance de patterns

---

## Annexe A : Personnalité de Scapin

### Nom et Inspiration

**Scapin** — Du personnage de Molière dans *Les Fourberies de Scapin* (1671).

**Caractéristiques du personnage original** :
- Rusé et inventif
- Dévoué mais pas servile
- Prend des initiatives
- Trouve toujours une solution
- Parfois désobéit pour le bien de son maître

### Ton et Style

- Proactif, pas passif
- Confiant, pas obséquieux
- Honnête, même quand c'est inconfortable
- Complice, pas distant
- Efficace, pas bavard

### L'Équipe des Valets

Scapin dirige une équipe de valets spécialisés :

| Valet | Origine | Spécialité |
|-------|---------|------------|
| **Trivelin** | Marivaux | Triage et perception |
| **Sancho** | Cervantes | Sagesse et raisonnement |
| **Passepartout** | Verne | Navigation et recherche |
| **Planchet** | Dumas | Planification |
| **Figaro** | Beaumarchais | Orchestration |
| **Sganarelle** | Molière | Apprentissage |
| **Frontin** | Molière | Interface API |

---

## Annexe B : Glossaire

| Terme | Définition dans le contexte Scapin |
|-------|-----------------------------------|
| **Anamnèse** | Pensée par soi-même, mémoire vive, réflexion active |
| **Hypomnèse** | Mémoire externalisée, traces techniques, délégation |
| **Pharmakon** | Caractère dual (poison/remède) de toute technologie |
| **Rétention tertiaire** | Trace technique qui conserve une mémoire accessible |
| **Mémoire transactive** | Système de mémoire partagée dans un groupe |
| **Métamémoire** | Savoir ce qu'on sait et où le trouver |
| **Cercle de confiance** | Niveau de partage autorisé avec une entité |
| **Niveau d'information** | Couche de détail (1=résumé, 2=contexte, 3=complet) |
| **Seuil d'autonomie** | Niveau de confiance requis pour action autonome |
| **Système maître** | Système unique de référence pour un type de données (ex: OmniFocus pour les tâches) |

---

## Annexe C : Questions Ouvertes pour Sessions Futures

1. **Révision espacée** : Quelles informations exactement doivent être révisées activement ? Fréquence optimale ?

2. **Mode vocal** : Quelle place pour les dialogues audio (validation en voiture, briefing matin) ?

3. **Collaboration Damien** : Quand et comment mettre en place Scapin-Damien ?

4. **Clients Eufonie** : Scapin peut-il évoluer vers un produit pour les clients ?

5. **Mesures quantitatives** : Comment mesurer objectivement la réduction de charge mentale ?

6. **WhatsApp** : Intégrer les messages WhatsApp au flux entrant ?

7. **Horizons GTD** : Comment Scapin intègre-t-il les horizons d'attention (runway → purpose) ?

---

## Annexe D : Historique des Décisions

| Date | Décision | Rationale |
|------|----------|-----------|
| 2026-01-02 | OmniFocus = système maître des tâches | Éviter fragmentation cognitive |
| 2026-01-02 | Calendrier : validation → autonomie progressive | Modèle de confiance appris |
| 2026-01-02 | Teams : intégration complète (brouillons validés) | Canal critique Eufonie/Skiillz |
| 2026-01-02 | LinkedIn : messagerie uniquement, priorité basse | Focus flux entrants, pas publication |
| 2026-01-02 | Planner : lecture seule (contexte équipe) | OmniFocus reste maître |
| 2026-01-02 | Loisirs : v1.5+ | Priorité réduction charge mentale pro |

---

**Document Fondateur — Version 1.1**  
**Ce document guide toutes les décisions de conception de Scapin.**

*"Le valet qui peut tout faire vaut plus que le maître qui ne peut rien."* — Molière
