# 09 - Critères de Succès

[< Retour à l'index](./00-index.md) | [< Implémentation](./08-implementation.md)

---

## Résumé

| Catégorie | Critères MVP | Critères Nice-to-have |
|-----------|--------------|----------------------|
| Frontend | 4 | — |
| Briefing & Flux | 5 | — |
| Notes PKM | 6 | — |
| Discussions | 6 | — |
| Journal | 4 | — |
| **Mobile** | **6** | — |
| Statistiques | — | 7 |
| Pipeline Valets | — | 3 |
| Rapports | — | 4 |
| Settings | — | 6 |
| UX Avancée | — | 17 |
| Backend | 3 | — |
| Qualité | 3 | — |
| **Total** | **37** | **37** |

---

# Critères MVP

## 1. Frontend — MVP

| # | Critère | Métrique |
|---|---------|----------|
| 1 | `npm run dev` lance l'interface | Port 5173 |
| 2 | Login/logout fonctionnels avec JWT | Token refresh < 15min |
| 3 | Thème dark/light auto | `prefers-color-scheme` |
| 4 | Responsive de base | Desktop + tablette |

---

## 2. Briefing & Flux — MVP

| # | Critère | Métrique |
|---|---------|----------|
| 1 | Briefing du matin avec résumé IA | Chargement < 3s |
| 2 | Mode "À traiter" guidé | Navigation 1/N visible |
| 3 | Flux unifié avec 4 onglets | À traiter, Traités, Historique, Rejets |
| 4 | Actions approve/modify/reject/undo | Feedback immédiat (toast) |
| 5 | Instructions en langage naturel | Via chat panel latéral |

---

## 3. Notes PKM — MVP

| # | Critère | Métrique |
|---|---------|----------|
| 1 | CRUD complet | Créer, lire, modifier, supprimer |
| 2 | Arborescence navigable | Tree view avec expand/collapse |
| 3 | Recherche full-text | Résultats < 500ms |
| 4 | Liens bidirectionnels affichés | Backlinks visibles |
| 5 | Épingler des notes favorites | Pin/unpin fonctionnel |
| 6 | Démarrer discussion depuis note | Contexte préservé |

---

## 4. Discussions Scapin — MVP

| # | Critère | Métrique |
|---|---------|----------|
| 1 | Multi-sessions (style Claude Desktop) | Liste sessions persistées |
| 2 | Chat panel latéral collapsible | Ouvert/réduit/plein écran |
| 3 | Démarrage depuis contexte | Event, note, rapport |
| 4 | Épingler discussions importantes | Pin/unpin fonctionnel |
| 5 | Réponses IA pertinentes | Contexte inclus |
| 6 | WebSocket temps réel | Latence < 100ms |

---

## 5. Journal — MVP

| # | Critère | Métrique |
|---|---------|----------|
| 1 | Génération draft du jour | Pré-rempli avec événements |
| 2 | Questions interactives | Style Q&A |
| 3 | Soumission corrections | Feedback Sganarelle |
| 4 | Liste journaux par date | Navigation calendrier |

---

## 6. Mobile — MVP

| # | Critère | Métrique |
|---|---------|----------|
| 1 | Bottom navigation fonctionnelle | 5 items : Accueil, Flux, Notes, Chat, Plus |
| 2 | Touch targets | Minimum 44x44px sur tous les boutons |
| 3 | Gestes swipe | Swipe gauche/droite sur EventCard |
| 4 | Pull-to-refresh | Sur toutes les listes |
| 5 | PWA installable | manifest.json + service worker basique |
| 6 | Layout adaptatif | Breakpoints mobile/tablet/desktop |

---

## 7. Backend — MVP

| # | Critère | Métrique |
|---|---------|----------|
| 1 | Tests backend | 1450+ tests (+100 nouveaux) |
| 2 | Qualité code | Ruff 0 warnings |
| 3 | Documentation API | OpenAPI/Swagger complet |

---

## 8. Qualité — MVP

| # | Critère | Métrique |
|---|---------|----------|
| 1 | Tests E2E | Playwright, parcours critiques passent |
| 2 | Performance | First load < 3s, Lighthouse > 80 |
| 3 | Documentation utilisateur | Guide de démarrage |

---

# Critères Nice-to-have

## 9. Statistiques — Nice-to-have

| # | Critère | Métrique |
|---|---------|----------|
| 1 | Dashboard principal avec KPIs | Vue d'ensemble |
| 2 | Graphiques évolution confiance | Courbe temporelle |
| 3 | Répartition par source | Donut chart |
| 4 | Patterns Sganarelle affichés | Liste patterns appris |
| 5 | Stats par valet | Appels, succès, échecs, temps |
| 6 | Consommation tokens | Input, output, coût, budget |
| 7 | Export CSV/JSON | Téléchargement fonctionnel |

---

## 10. Pipeline Valets — Nice-to-have

| # | Critère | Métrique |
|---|---------|----------|
| 1 | Visualisation brigade complète | Johan, Scapin, 6 valets |
| 2 | État temps réel | Idle, working, error |
| 3 | Sujet en cours visible | Aperçu de ce que traite chaque valet |

---

## 11. Rapports — Nice-to-have

| # | Critère | Métrique |
|---|---------|----------|
| 1 | Rapports journaliers | Générés automatiquement |
| 2 | Rapports hebdomadaires et mensuels | Agrégation correcte |
| 3 | Export PDF/Markdown | Téléchargement fonctionnel |
| 4 | Statistiques et apprentissages | Inclus dans rapport |

---

## 12. Settings — Nice-to-have

| # | Critère | Métrique |
|---|---------|----------|
| 1 | Nombre de recommandations | Paramétrable 0-3 |
| 2 | Fréquence de synchro | Par compte |
| 3 | Latence/période de grâce | Par compte |
| 4 | Valeurs par défaut | Par source |
| 5 | Seuil de confiance auto | Configurable |
| 6 | Gestion comptes et intégrations | CRUD complet |

---

## 13. UX Avancée — Nice-to-have

### Navigation (4 critères)

| # | Critère | Raccourci |
|---|---------|-----------|
| 1 | Recherche globale | `Cmd+K` |
| 2 | Header avec status Scapin temps réel | — |
| 3 | Raccourcis clavier globaux | `?` pour aide |
| 4 | Quick Capture | `Cmd+Shift+N` |

### Productivité (4 critères)

| # | Critère | Description |
|---|---------|-------------|
| 1 | Mode Focus / Do Not Disturb | Pause synchro |
| 2 | Quick Actions dans briefing | Boutons rapides |
| 3 | Bulk actions | Sélection multiple |
| 4 | Filtres sauvegardés | Réutilisables |

### Flux (4 critères)

| # | Critère | Description |
|---|---------|-------------|
| 1 | Snooze événements | Reporter à plus tard |
| 2 | Tags personnalisés | Sur événements |
| 3 | Annotations | Sur événements traités |
| 4 | Vue calendrier optionnelle | Affichage alternatif |

### Notes (3 critères)

| # | Critère | Description |
|---|---------|-------------|
| 1 | Preview hover liens PKM | `[[...]]` avec aperçu |
| 2 | Templates de notes | Contact, Réunion, Projet |
| 3 | Historique versions avec diff | Comparaison visuelle |

### Analytics (2 critères)

| # | Critère | Description |
|---|---------|-------------|
| 1 | Centre de notifications | Liste notifications |
| 2 | Activity log / Timeline | Historique actions |

---

# Phase Ultérieure (0.9)

Fonctionnalités planifiées pour une version future :

## Prédictions Scapin

| Fonctionnalité | Description |
|----------------|-------------|
| Anticipation intelligente | "Demain, tu auras probablement 8 emails à traiter" |
| Suggestions proactives | Basées sur les patterns détectés |
| Alertes préventives | Prévenir avant surcharge |

## Résumé Audio du Briefing

| Fonctionnalité | Description |
|----------------|-------------|
| TTS (Text-to-Speech) | Écouter le briefing |
| Mobilité | Pendant le café ou en déplacement |
| PWA Mobile | Intégration future |

---

# Checklist de Validation Finale

Avant de considérer la Phase 0.8 comme complétée :

```
□ Tous les critères MVP cochés (37 items)
□ Tests E2E passent sans échec
□ Performance Lighthouse > 80 (desktop ET mobile)
□ Documentation utilisateur rédigée
□ Ruff 0 warnings sur backend
□ 1450+ tests backend passent
□ PWA installable et fonctionnelle
□ Revue de code effectuée
```

---

[< Implémentation](./08-implementation.md) | [Retour à l'index](./00-index.md)
