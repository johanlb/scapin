# Plan Phase 0.8 — Interface Web Scapin

## Vue d'Ensemble

Ce plan décrit l'implémentation d'une interface web **event-centric** pour Scapin.

**Objectif** : Créer une interface web moderne pour superviser et interagir avec Scapin au quotidien.

**Vision Centrale** : Scapin est un processeur d'événements. L'interface reflète ce paradigme unifié — pas de silos par source (email, Teams, Calendar), mais un flux unique d'événements à traiter.

**Dépendance** : Phase 0.7 (API Jeeves) — ✅ Complétée

---

## Par où commencer ?

| Objectif | Document recommandé |
|----------|---------------------|
| Comprendre le concept | [01-vision.md](./01-vision.md) |
| Voir les écrans | [04-mockups-core.md](./04-mockups-core.md) |
| Commencer à coder | [08-implementation.md](./08-implementation.md) |
| Vérifier les critères | [09-criteres-succes.md](./09-criteres-succes.md) |

---

## Documents du Plan

| # | Fichier | Catégorie | Description |
|---|---------|-----------|-------------|
| 01 | [vision.md](./01-vision.md) | 📋 Concept | Résumé exécutif, paradigme event-centric, principes UX |
| 02 | [architecture.md](./02-architecture.md) | 🏗️ Technique | Stack (SvelteKit + TailwindCSS), structure ~100 fichiers |
| 03 | [design-system.md](./03-design-system.md) | 🎨 Design | Palette couleurs, typographie, composants UI |
| 04 | [mockups-core.md](./04-mockups-core.md) | 🖼️ Mockups | Layout, Briefing, Flux, Notes PKM, Discussions |
| 05 | [mockups-analytics.md](./05-mockups-analytics.md) | 🖼️ Mockups | Statistiques, Rapports, Settings |
| 06 | [ux-avancee.md](./06-ux-avancee.md) | ✨ UX | 17 améliorations (Cmd+K, Focus, Snooze, Tags...) |
| 07 | [api-endpoints.md](./07-api-endpoints.md) | 🔌 API | ~50 nouveaux endpoints backend nécessaires |
| 08 | [implementation.md](./08-implementation.md) | 🛠️ Étapes | 20 étapes d'implémentation ordonnées |
| 09 | [criteres-succes.md](./09-criteres-succes.md) | ✅ Validation | Checklist complète de validation |

---

## Routes Principales

| Route | Page | Description |
|-------|------|-------------|
| `/` | Briefing | Page d'accueil avec résumé du jour et actions urgentes |
| `/flux` | Flux | Événements unifiés (À traiter, Traités, Historique, Rejets) |
| `/flux/[id]` | Détail | Vue détaillée d'un événement avec actions |
| `/notes` | Notes PKM | Arborescence, recherche, édition Markdown |
| `/notes/[path]` | Note | Édition d'une note avec liens bidirectionnels |
| `/discussions` | Discussions | Liste des conversations avec Scapin |
| `/discussions/[id]` | Chat | Conversation temps réel (WebSocket) |
| `/stats` | Statistiques | Dashboard KPIs, graphiques, consommation tokens |
| `/rapports` | Rapports | Journaliers, hebdomadaires, mensuels + export |
| `/settings` | Paramètres | Comptes, seuils IA, intégrations |

---

## Stack Technique

| Couche | Technologie | Rôle |
|--------|-------------|------|
| **Frontend** | SvelteKit | Framework web avec SSR |
| **Styling** | TailwindCSS | Utility-first CSS |
| **Types** | TypeScript | Typage strict |
| **Backend** | FastAPI | API REST (existant Phase 0.7) |
| **Temps réel** | WebSocket | Chat et notifications |
| **Auth** | JWT | Authentification stateless |

---

## Spécifications Clés

- **Home** : Le briefing du matin est la page d'accueil
- **Flux unifié** : Tous les événements dans une seule vue (pas de silos email/Teams/Calendar)
- **OmniFocus** : Intégré dans le flux d'événements comme source
- **Notes PKM** : CRUD complet avec liens bidirectionnels `[[...]]`
- **Thème** : Auto-détection (suit `prefers-color-scheme`)
- **Auth** : JWT complète avec refresh token
- **WhatsApp** : Prévu pour une phase ultérieure

---

## Statut

- [x] Phase 0.7 : API Jeeves MVP ✅
- [ ] **Phase 0.8 : Interface Web** (ce plan)
- [ ] Phase 0.9 : Prédictions Scapin, Résumé Audio (V2)

---

*Dernière mise à jour : 4 janvier 2026*
