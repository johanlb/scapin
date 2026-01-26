# Chat + Mémoire Sélective

**Date** : 27 janvier 2026
**Statut** : Design validé
**Auteur** : Johan + Claude

---

## Résumé exécutif

Scapin dispose d'un assistant conversationnel intégré avec mémoire sélective. Le chat permet de poser des questions, demander des analyses, rédiger des contenus, et exécuter des actions — le tout avec le contexte complet du PKM.

**Fonctionnalités clés** :
- Chat hybride (panel latéral + mode plein écran)
- Contexte automatique (page courante + RAG + Canevas)
- Mémoire sélective (préférences, décisions, faits, instructions)
- Actions exécutables avec confirmation selon le risque
- Auto-escalade Haiku → Sonnet → Opus

---

## Usages du Chat

| Usage | Exemple | Modèle typique |
|-------|---------|----------------|
| **Factuel** | "Quel est le téléphone de Marc ?" | Haiku |
| **Contextuel** | "Résume mes échanges avec TechCorp" | Haiku/Sonnet |
| **Aide à la décision** | "Dois-je accepter cette offre ?" | Sonnet |
| **Rédaction** | "Rédige un email de relance pour Marc" | Sonnet |
| **Stratégique** | "Analyse ma charge cognitive cette semaine" | Sonnet/Opus |

---

## Interface Utilisateur

### Accès

| Méthode | Description |
|---------|-------------|
| **Raccourci** | `Cmd+K` ouvre le panel |
| **Bouton** | Icône fixe en bas à droite |

### Modes d'affichage

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MODE PANEL (par défaut)                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────┐  │
│  │                                 │  │  💬 Chat Scapin            [⤢]  │  │
│  │                                 │  ├─────────────────────────────────┤  │
│  │     Page principale             │  │                                 │  │
│  │     (note, email, etc.)         │  │  Historique conversation...     │  │
│  │                                 │  │                                 │  │
│  │                                 │  │                                 │  │
│  │                                 │  ├─────────────────────────────────┤  │
│  │                                 │  │  [Haiku ▾]  Message...    [→]   │  │
│  └─────────────────────────────────┘  └─────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  MODE PLEIN ÉCRAN (clic sur ⤢)                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  💬 Chat Scapin                                              [⤡]    │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                     │   │
│  │  Conversation avec plus d'espace...                                 │   │
│  │                                                                     │   │
│  │  Idéal pour rédaction longue ou analyse complexe                    │   │
│  │                                                                     │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  [Sonnet ▾]  Message...                                       [→]   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Sélecteur de modèle

Bouton discret permettant de forcer un modèle :
- **Auto** (défaut) — escalade automatique
- **Haiku** — réponses rapides
- **Sonnet** — rédaction/analyse
- **Opus** — réflexion stratégique

---

## Contexte Automatique

Le chat reçoit automatiquement :

| Source | Contenu | Quand |
|--------|---------|-------|
| **Canevas** | Profil Johan, objectifs, projets actifs | Toujours |
| **Page courante** | Note, email, ou événement affiché | Si pertinent |
| **RAG PKM** | Notes similaires à la question | Selon la query |
| **Mémoires** | Préférences et décisions passées | Selon la query |

Le modèle décide ce qui est pertinent à utiliser selon la question posée.

---

## Mémoire Sélective

### Principe

Le chat extrait automatiquement ce qui mérite d'être retenu :

| Type | Exemple | Durée |
|------|---------|-------|
| **Préférence** | "Je préfère les emails courts et directs" | Permanente |
| **Décision** | "J'ai choisi Svelte plutôt que React" | Permanente |
| **Fait personnel** | "Mon associé Marc travaille chez TechCorp" | Permanente |
| **Instruction** | "Toujours vouvoyer les clients" | Permanente |

### Ce qui n'est PAS retenu

- Questions factuelles ponctuelles
- Brouillons intermédiaires
- Conversations exploratoires sans conclusion

### Stockage

```sql
CREATE TABLE chat_memories (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,  -- preference, decision, fact, instruction
    content TEXT NOT NULL,
    source_conversation_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confidence REAL DEFAULT 0.9,
    related_note_id TEXT,  -- nullable, lien vers note PKM
    is_active BOOLEAN DEFAULT TRUE
);
```

### Gestion

- Extraction automatique en fin de conversation
- Score de confiance pour chaque mémoire
- Interface dans les paramètres pour voir/éditer/supprimer
- Mémoires embedées et injectées via RAG quand pertinentes

---

## Actions Exécutables

### Permissions par action

| Action | Risque | Confirmation |
|--------|--------|--------------|
| Lire (notes, emails, calendrier) | Aucun | Non |
| Créer note | Faible | Non |
| Créer tâche OmniFocus | Faible | Non |
| Rédiger brouillon email | Faible | Non |
| Modifier note existante | Moyen | Oui (diff affiché) |
| Envoyer email | Élevé | Oui + relecture |
| Archiver/supprimer | Élevé | Oui |

### Interface d'action

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  RÉPONSE AVEC ACTIONS                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Tu devrais relancer Marc concernant le budget Q2.                          │
│  Voici un brouillon d'email :                                               │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Objet : Suivi budget Q2                                            │   │
│  │                                                                     │   │
│  │  Bonjour Marc,                                                      │   │
│  │  Je reviens vers toi concernant le budget Q2...                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  [Créer brouillon Gmail]  [Créer tâche OF]  [Copier]                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Le chat comprend aussi les confirmations textuelles :
- "Oui, crée la tâche"
- "Envoie le brouillon"
- "Ajoute ça à la note Marc"

---

## Historique des Conversations

### Fonctionnalités

| Feature | Description |
|---------|-------------|
| **Liste** | Conversations passées avec titre auto-généré |
| **Recherche** | Recherche full-text dans l'historique |
| **Consultation** | Relire une conversation passée |
| **Pas de reprise** | Les vieilles conversations ne peuvent pas être continuées |

### Justification

Reprendre une vieille conversation est rarement pertinent car :
- Le contexte (page courante, état PKM) a changé
- La mémoire sélective capture l'essentiel
- Une nouvelle conversation avec le bon contexte est plus efficace

---

## Sélection du Modèle

### Auto-escalade (défaut)

```
Question simple ("téléphone de Marc ?")
    → Haiku répond

Question moyenne ("résume mes échanges avec TechCorp")
    → Haiku tente, escalade vers Sonnet si besoin

Question complexe ("analyse stratégique de ma charge")
    → Direct vers Sonnet, escalade Opus si nécessaire

Rédaction longue
    → Sonnet systématiquement
```

### Override manuel

Bouton `[Haiku ▾]` permet de forcer :
- **Haiku** — économiser sur les questions simples
- **Sonnet** — forcer la qualité
- **Opus** — réflexion stratégique profonde

---

## Architecture Technique

### Valet responsable

**Frontin** gère le chat (interface utilisateur). En interne :
- **Sancho** : raisonnement IA, génération de réponses
- **Passepartout** : RAG, accès PKM, stockage mémoires
- **Figaro** : orchestration des actions

### Endpoints API

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/chat/message` | POST | Envoyer un message |
| `/api/chat/conversations` | GET | Liste des conversations |
| `/api/chat/conversations/{id}` | GET | Détail d'une conversation |
| `/api/chat/memories` | GET | Liste des mémoires |
| `/api/chat/memories/{id}` | DELETE | Supprimer une mémoire |
| `/api/chat/actions/{type}` | POST | Exécuter une action |

### Structure des données

```
src/frontin/
├── api/
│   └── chat.py              # Endpoints chat
├── chat/
│   ├── __init__.py
│   ├── manager.py           # Orchestration conversations
│   ├── memory_extractor.py  # Extraction mémoires sélectives
│   └── action_executor.py   # Exécution des actions
```

---

## Coûts Estimés

### Usage modéré (50 questions/mois)

| Type | Volume | Coût unitaire | Total |
|------|--------|---------------|-------|
| Questions simples (Haiku) | 30 | $0.01 | $0.30 |
| Questions moyennes (Sonnet) | 15 | $0.05 | $0.75 |
| Questions complexes (Opus) | 5 | $0.25 | $1.25 |
| **Total** | 50 | | **~$2.30/mois** |

### Usage intensif (200 questions/mois)

| Type | Volume | Coût unitaire | Total |
|------|--------|---------------|-------|
| Questions simples | 120 | $0.01 | $1.20 |
| Questions moyennes | 60 | $0.05 | $3.00 |
| Questions complexes | 20 | $0.25 | $5.00 |
| **Total** | 200 | | **~$9.20/mois** |

Dans le budget global Scapin (~$117/mois haute capacité).

---

## Questions Ouvertes

1. **Raccourci exact** — `Cmd+K` peut confliter avec d'autres apps, alternative `Cmd+J` ?
2. **Export** — Permettre d'exporter une conversation en Markdown ?
3. **Partage** — Partager une conversation (lien public) ?
4. **Voice** — Input vocal pour le chat ?

---

## Prochaines Étapes

1. Créer les endpoints API dans `src/frontin/api/chat.py`
2. Implémenter le gestionnaire de conversations
3. Implémenter l'extracteur de mémoires sélectives
4. Créer le composant UI `ChatPanel.svelte`
5. Ajouter le mode plein écran
6. Intégrer les boutons d'action
7. Tests E2E du parcours complet

---

## Relation avec les autres modules

| Module | Interaction |
|--------|-------------|
| **Frontin** | Héberge le chat (API + orchestration) |
| **Sancho** | Génère les réponses (appels IA) |
| **Passepartout** | RAG PKM, stockage mémoires, accès notes |
| **Figaro** | Exécute les actions (email, tâches) |
| **Bazin** | Le chat peut demander un briefing à la demande |

---

*Document créé le 27 janvier 2026*
