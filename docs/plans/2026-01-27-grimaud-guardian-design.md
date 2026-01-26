# Grimaud — Gardien du PKM

**Date** : 27 janvier 2026
**Statut** : Design validé
**Auteur** : Johan + Claude

---

## Résumé exécutif

Grimaud est le gardien proactif du PKM de Johan. Il scanne continuellement les notes, détecte les problèmes (fragmentation, incomplétude, obsolescence), et agit automatiquement si la confiance est suffisante.

**Changements clés** :
- Grimaud **remplace Retouche** — une seule interface pour toute la maintenance IA
- Nouveau rôle pour le valet Grimaud (anciennement : analyse aveugle dans le pipeline 4 valets)
- Scan **temps réel** (pas de batch) pour simplicité
- Enrichissement **web** automatique pour la plupart des types de notes

---

## Contexte

### Problèmes actuels du PKM

1. **Fragmentation** — Même sujet éparpillé sur plusieurs notes
2. **Désorganisation** — Notes ne suivant pas leur template
3. **Incomplétude** — Sections vides, infos manquantes
4. **Obsolescence** — Infos périmées, liens morts

### Limitation de Retouche

Retouche est **passive** (déclenchée par SM-2) et travaille sur **une note à la fois**. Elle ne détecte pas les problèmes **entre** notes (fragmentation, doublons).

---

## Évolution du rôle de Grimaud

| Période | Rôle |
|---------|------|
| **Avant** (v1) | Valet d'analyse aveugle — 1ère passe sans contexte PKM |
| **Après** (v2) | Gardien du PKM — Maintenance proactive et silencieuse |

### Pourquoi ce nom

> *"Grimaud était habitué à ne parler que par gestes. Son maître lui ayant interdit la parole, il avait pris l'habitude de tout exprimer par signes."*
> — Alexandre Dumas, Les Trois Mousquetaires

Le Gardien PKM travaille silencieusement en arrière-plan, agit sans déranger, et Johan découvre le travail accompli.

---

## Architecture

### Intégration dans Scapin

```
src/grimaud/                    # Nouveau module (remplace l'ancien rôle)
├── scanner.py                  # Sélection et priorisation des notes
├── analyzer.py                 # Détection des problèmes + appel IA
├── executor.py                 # Application des actions + snapshots
├── web_enricher.py             # Recherche web par type de note
└── history.py                  # Gestion snapshots et corbeille
```

### Relation avec les autres valets

| Valet | Interaction avec Grimaud |
|-------|--------------------------|
| **Passepartout** | Fournit accès notes, FAISS pour similarité |
| **Sancho** | Appels IA (Sonnet) |
| **Sganarelle** | Stockage patterns appris |
| **Frontin** | API endpoints, UI |

---

## Actions du Gardien

### Types d'actions

| Action | Description | Seuil auto | Réversibilité |
|--------|-------------|------------|---------------|
| **Fusion** | Combiner 2+ notes sur le même sujet | 0.95+ | Snapshot + corbeille |
| **Liaison** | Créer un lien `[[wikilink]]` entre notes | 0.85+ | Supprimer le lien |
| **Restructuration** | Réorganiser selon le template du type | 0.90+ | Snapshot |
| **Enrichissement texte** | Compléter sections vides (interne) | 0.90+ | Snapshot |
| **Enrichissement web** | Ajouter infos depuis recherche web | 0.80+ | Section marquée, supprimable |
| **Métadonnées** | Corriger/compléter frontmatter | 0.85+ | Snapshot |
| **Archivage** | Marquer note obsolète | 0.90+ | Désarchiver |

### Détection des problèmes

| Problème | Méthode de détection |
|----------|---------------------|
| **Fragmentation** | Embedding similarity > 0.85, titres similaires, mêmes entités |
| **Désorganisation** | Note ne match pas son template (sections manquantes/désordonnées) |
| **Incomplétude** | Sections vides, frontmatter incomplet, liens cassés |
| **Obsolescence** | Dernière modif > 1 an + importance basse, dates passées |

---

## Enrichissement par type de note

### Configuration

| Type | auto_enrich | web_search | Sources web |
|------|-------------|------------|-------------|
| Personne | ✅ | ✅ | LinkedIn, parcours, actualités |
| Entité | ✅ | ✅ | Kbis, actualités, contacts |
| Concept | ✅ | ✅ | Définitions, état de l'art |
| Lieu | ✅ | ✅ | Horaires, avis, photos |
| Produit | ✅ | ✅ | Specs, alternatives |
| Ressource | ✅ | ✅ | Infos auteur/contenu |
| Projet | ✅ | ✅ | Contexte marché, tendances |
| Processus | ✅ | ✅ | Bonnes pratiques |
| Décision | ✅ | ❌ | Contexte + suivi conséquences |
| Objectif | ✅ | ✅ | Ressources suggérées |
| Souvenir | ✅ lier only | ❌ | **Ne jamais modifier le texte** |
| Événement | ✅ | ✅ | CR officiels, photos |
| Réunion | ✅ | ❌ | Interne uniquement |

### Format d'intégration web

```markdown
## Recherche Web
<!-- Ajouté par Grimaud le 2026-01-27 -->

**Poste actuel**
Directeur Innovation chez TechCorp (depuis 2024)
> Source: [LinkedIn](https://linkedin.com/in/...)

**Actualités**
- "TechCorp lève 10M€" (Les Échos, 15 jan 2026)
> Source: [Les Échos](https://lesechos.fr/...)
```

### Règles d'enrichissement web

- Section séparée `## Recherche Web` pour traçabilité
- Toujours citer la source avec URL
- Date d'ajout indiquée
- Ne jamais modifier le texte existant de l'utilisateur
- Refresh max 1x/mois par note

---

## Scan continu

### Fonctionnement

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  GRIMAUD — Scan continu temps réel                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  BOUCLE (toutes les X minutes quand idle)                                   │
│                                                                             │
│  1. Sélectionner la note avec le plus haut score de priorité                │
│     (non scannée depuis > 7 jours)                                          │
│                                                                             │
│  2. Pré-analyse locale (sans IA)                                            │
│     ├─ Détecter fragments similaires (FAISS)                                │
│     ├─ Vérifier structure vs template                                       │
│     └─ Si aucun problème détecté → marquer scannée, passer à la suivante    │
│                                                                             │
│  3. Analyse IA (si problèmes détectés)                                      │
│     ├─ Appel Sonnet avec contexte (template, notes liées, Canevas)          │
│     ├─ Recevoir propositions d'actions                                      │
│     └─ Coût : ~$0.05/note                                                   │
│                                                                             │
│  4. Exécution immédiate                                                     │
│     ├─ Actions confidence > seuil → Appliquer + snapshot                    │
│     └─ Actions confidence < seuil → Queue "À valider"                       │
│                                                                             │
│  5. Répéter                                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Score de priorité

```
score = (importance × 3) + (ancienneté_scan × 2) + (problèmes_détectés × 1)
```

| Facteur | Calcul | Poids |
|---------|--------|-------|
| **Importance** | Liée à projet HIGH = 10, ACTIVE = 5, autre = 1 | ×3 |
| **Ancienneté scan** | Jours depuis dernier scan Grimaud (max 30) | ×2 |
| **Problèmes détectés** | Pré-scan rapide : liens cassés, sections vides | ×1 |

### Throttling

| Paramètre | Valeur par défaut |
|-----------|-------------------|
| Notes par heure (max) | 10 |
| Pause si machine occupée | Oui |
| Pause si sur batterie | Oui (optionnel) |
| Heures actives | 00h-08h + idle |

### Scan manuel urgent

Bouton "Scanner maintenant" dans l'UI :
- Bypass le throttling
- Appel API direct
- Résultat en 10-30 secondes

---

## Versioning et réversibilité

### Snapshots

Avant chaque modification, Grimaud crée un snapshot :

```json
{
  "id": "snap_20260127_143022_abc123",
  "note_id": "note_xyz",
  "note_title": "Marc Dupont",
  "timestamp": "2026-01-27T14:30:22Z",
  "action": "fusion",
  "action_detail": "Fusionné avec 'Marc D. - Contact'",
  "confidence": 0.96,
  "content_before": "... contenu complet ...",
  "frontmatter_before": { },
  "triggered_by": "grimaud_auto"
}
```

### Stockage

| Paramètre | Valeur |
|-----------|--------|
| Emplacement | `data/grimaud/snapshots/` |
| Format | JSON compressé (gzip) |
| Rétention | 30 jours |
| Purge | Automatique, quotidienne |

### Corbeille (notes fusionnées)

Quand Note A est fusionnée dans Note B :
- Le contenu de A est intégré dans B
- Note A est déplacée dans `Corbeille Grimaud/`
- Conservée 30 jours avant suppression définitive
- Restauration = recrée la note + annule les modifications dans B

---

## Interface utilisateur

### Nouvelle organisation des routes

| Fonctionnalité | Route | Rôle |
|----------------|-------|------|
| **Lecture** | `/memoires/review` | Révision SM-2 humaine (inchangé) |
| **Filage** | `/memoires/filage` | Briefing quotidien (inchangé) |
| **Grimaud** | `/memoires/grimaud` | **Toute la maintenance IA** (remplace Retouche) |

### Page principale `/memoires/grimaud`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  GRIMAUD — Santé du PKM                                              ⚙️     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ 847      │  │ 92%      │  │ 8        │  │ 5        │  │ 12       │      │
│  │ Notes    │  │ Santé    │  │ À valider│  │ Fusions  │  │ Enrichis │      │
│  │ total    │  │ globale  │  │          │  │ ce mois  │  │ ce mois  │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│                                                                             │
│  ┌─ Filtres ─────────────────────────────────────────────────────────────┐ │
│  │ [Tous] [À valider (8)] [Fragmentées] [Incomplètes] [Obsolètes]        │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  Activité récente                                                           │
│  ───────────────────────────────────────────────────────────────────────    │
│  🔀 14:30  Marc Dupont — Fusion auto (96%)                    [Annuler]     │
│  🔗 14:28  Projet Alpha ↔ Concept Agile — Liaison auto (91%)  [Annuler]     │
│  📝 14:25  AWCS — Restructuration proposée (78%)    [Appliquer] [Rejeter]   │
│  🌐 14:20  TechCorp — Enrichissement web auto (85%)           [Annuler]     │
│  📊 14:15  Note Budget — Amélioration contenu auto (88%)      [Annuler]     │
│                                                                             │
│  [Scanner une note]                      [Corbeille (3)] [Historique]       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Historique sur chaque note

```
┌─────────────────────────────────────────┐
│  Historique Grimaud                     │
├─────────────────────────────────────────┤
│  27 jan 2026 14:30 — Fusion             │
│  ├─ "Fusionné avec Marc D. - Contact"   │
│  ├─ Confiance: 96%                      │
│  └─ [Voir avant] [Restaurer]            │
│                                         │
│  20 jan 2026 03:15 — Enrichissement     │
│  ├─ "Ajout section Recherche Web"       │
│  ├─ Confiance: 87%                      │
│  └─ [Voir avant] [Restaurer]            │
└─────────────────────────────────────────┘
```

### Migration des composants Retouche

| Composant actuel | Devient |
|------------------|---------|
| `PendingActionCard` | `GrimaudActionCard` (étendu) |
| `MergeModal` | Réutilisé tel quel |
| `RetoucheHistory` | `GrimaudHistory` |
| `RetoucheBadge` | `GrimaudBadge` (santé note) |
| `RetoucheDiff` | Réutilisé tel quel |
| `useRetoucheActions` | `useGrimaudActions` |

---

## Coûts estimés

### Hypothèses

- ~1000 notes dans le PKM
- Scan de 50-100 notes/jour
- 30% nécessitent analyse IA (problème détecté)
- Coût Sonnet : ~$0.05/note

### Estimation mensuelle

| Composant | Calcul | Coût |
|-----------|--------|------|
| Pré-analyse locale | Gratuit | $0 |
| Analyse IA (30% de 100/jour) | 30 × 30 × $0.05 | $45 |
| Recherche web | ~100 notes/mois | $5-10 |
| **Total** | | **~$50-55/mois** |

Dans le budget global Scapin (~$117/mois haute capacité).

---

## Documentation à mettre à jour

Lors de l'implémentation :

- [ ] `ARCHITECTURE.md` — Section Grimaud réécrite
- [ ] `CLAUDE.md` — Glossaire mis à jour (Grimaud = Gardien)
- [ ] `/valets` skill — Description du nouveau rôle
- [ ] Commentaires dans `src/grimaud/` — Header expliquant la transition
- [ ] `src/passepartout/note_types.py` — Mettre à jour `web_search_default`

---

## Questions ouvertes

1. **Seuil exact de similarité FAISS** pour détecter la fragmentation (0.85 proposé)
2. **APIs de recherche web** à utiliser (SerpAPI ? Tavily ? Scraping direct ?)
3. **Gestion des conflits Apple Notes** si note modifiée pendant le scan
4. **Notification** — Push notification ou juste badge dans l'UI ?

---

## Prochaines étapes

1. Créer le module `src/grimaud/`
2. Migrer les composants Retouche vers Grimaud
3. Implémenter le scanner avec priorisation
4. Ajouter l'enrichissement web
5. Créer la route `/memoires/grimaud`
6. Tests E2E du cycle complet

---

*Document créé le 27 janvier 2026*
