# Analyse Stratégique: Architecture et Déploiement de Scapin

**Date:** Janvier 2026
**Statut:** Réflexion stratégique — Décision: Conserver l'architecture actuelle

---

## Contexte

Johan utilise Scapin principalement via la **PWA web** (desktop + mobile).
Le backend Python tourne actuellement en local sur son Mac.

**Préoccupations exprimées:**
1. Performance du système
2. Comment accéder au backend depuis mobile si celui-ci tourne sur le Mac?
3. Faut-il un serveur cloud central?
4. Intégration iOS native (notifications, widgets)

---

## Le Vrai Problème: Pas le Langage, mais l'Architecture

Python n'est **pas** le problème. L'architecture actuelle est solide:
- Backend FastAPI performant (async, ~50k lignes bien structurées)
- Frontend SvelteKit moderne avec PWA
- Stockage local-first efficace (JSON + SQLite + FAISS)

Le vrai défi est: **où faire tourner le backend pour un accès multi-device?**

---

## Options d'Architecture Évaluées

### Option A: Mac comme Serveur (actuel + amélioration) ✅ RECOMMANDÉ

```
┌─────────────┐     ┌─────────────┐
│ iPhone PWA  │────▶│             │
└─────────────┘     │   Mac       │
                    │   Backend   │
┌─────────────┐     │   Python    │
│ Mac Browser │────▶│   :8000     │
└─────────────┘     └─────────────┘
```

**Comment y accéder depuis l'iPhone?**
- **Tailscale** (recommandé): VPN mesh gratuit, le Mac obtient une IP stable (ex: 100.x.x.x)
- L'iPhone accède à `http://100.x.x.x:8000` comme s'il était sur le réseau local
- Aucun port à ouvrir, sécurisé, fonctionne partout

**Avantages:**
- ✅ Aucune modification du code
- ✅ Données restent sur ton Mac (privacy)
- ✅ Gratuit (Tailscale free tier)
- ✅ Fonctionne immédiatement

**Inconvénients:**
- ⚠️ Mac doit être allumé pour que Scapin fonctionne
- ⚠️ Si le Mac dort, pas d'accès depuis iPhone

**Verdict:** Solution la plus simple, à essayer en premier.

---

### Option B: Backend sur VPS Cloud

```
┌─────────────┐     ┌─────────────────┐
│ iPhone PWA  │────▶│                 │
└─────────────┘     │  VPS (Fly.io)   │
                    │  Backend Python │
┌─────────────┐     │  + SQLite       │
│ Mac Browser │────▶│                 │
└─────────────┘     └─────────────────┘
```

**Fournisseurs recommandés:**
- **Fly.io**: ~$5-7/mois, déploiement simple, SQLite persistant
- **Railway**: ~$5/mois, GitHub integration
- **DigitalOcean**: ~$6/mois, plus de contrôle

**Avantages:**
- ✅ Toujours disponible (24/7)
- ✅ Accessible de partout sans VPN
- ✅ Pas de dépendance au Mac

**Inconvénients:**
- ⚠️ Coût mensuel (~$5-10/mois en plus des $27 Anthropic)
- ⚠️ Données personnelles sur un serveur tiers
- ⚠️ Sync des notes à gérer (actuellement sur filesystem Mac)
- ⚠️ Intégrations locales (OmniFocus, Apple Notes) plus complexes

**Verdict:** Bonne option si tu veux une disponibilité 24/7, mais ajoute de la complexité.

---

### Option C: App Native iOS (Swift) ❌ NON RECOMMANDÉ

Réécrire le backend en Swift pour iOS.

**Avantages:**
- ✅ Notifications iOS natives
- ✅ Widgets, Siri, intégration système parfaite
- ✅ Pas besoin de serveur

**Inconvénients:**
- ❌ Réécriture MASSIVE (~50k lignes Python → Swift)
- ❌ Perte de l'interface web desktop
- ❌ Swift à apprendre/maîtriser
- ❌ Maintenance double si tu veux garder le web

**Verdict:** Disproportionné pour un projet personnel. Non recommandé.

---

### Option D: Capacitor (PWA → App iOS) ⭐ OPTION FUTURE

Wrapper la PWA actuelle dans une app native via Capacitor.

```
┌─────────────────────────────────────┐
│  App iOS (Capacitor)                │
│  ┌───────────────────────────────┐  │
│  │  WebView (SvelteKit PWA)      │  │
│  │  + Plugins natifs             │  │
│  └───────────────────────────────┘  │
│  - Push Notifications (native)      │
│  - Haptics (native)                 │
│  - Local storage (native)           │
└─────────────────────────────────────┘
          │
          ▼
    Backend Python (Mac ou VPS)
```

**Avantages:**
- ✅ Notifications push iOS natives
- ✅ Haptics natifs (vibreur iOS)
- ✅ Garde tout le code Svelte existant
- ✅ Publication sur App Store possible
- ✅ Effort modéré (1-2 semaines)

**Inconvénients:**
- ⚠️ Nécessite un Mac pour builder l'app
- ⚠️ Compte Apple Developer ($99/an) si App Store
- ⚠️ Le backend reste ailleurs (Mac ou VPS)

**Verdict:** Excellent compromis pour l'intégration iOS sans tout réécrire.

---

### Option E: Tauri (Rust backend, desktop natif) ❌ NON PRIORITAIRE

Remplacer le backend Python par Rust, packager en app native.

**Avantages:**
- ✅ Performance native exceptionnelle
- ✅ Bundle léger (~10MB vs ~200MB Electron)
- ✅ Cross-platform (macOS, Windows, Linux)

**Inconvénients:**
- ❌ Réécriture backend en Rust (courbe d'apprentissage)
- ❌ Pas de solution iOS simple avec Tauri (desktop only)
- ❌ Effort énorme pour gain marginal

**Verdict:** Intéressant pour le futur, mais pas prioritaire.

---

## Recommandations par Phases

### Phase 1: Immédiat (0 effort)

**Tailscale pour accès mobile**

1. Installer Tailscale sur le Mac et l'iPhone
2. Accéder à Scapin via l'IP Tailscale depuis l'iPhone
3. Tester pendant 2-4 semaines

Coût: Gratuit
Effort: 30 minutes

### Phase 2: Court terme (si Phase 1 satisfaisante)

**Optimisation performance backend**

1. Profiler le backend (identifier les goulots)
2. Ajouter du caching (Redis ou in-memory)
3. Lazy loading du FAISS index
4. Améliorer les requêtes SQL

Coût: Gratuit
Effort: Quelques heures

### Phase 3: Moyen terme (si notifications iOS critiques)

**Capacitor pour app iOS native**

1. Wrapper la PWA avec Capacitor
2. Implémenter Push Notifications natives
3. Ajouter Haptics natifs
4. Optionnel: publier sur TestFlight (gratuit)

Coût: Gratuit (ou $99/an si App Store)
Effort: 1-2 semaines

### Phase 4: Long terme (si Mac pas toujours disponible)

**Migration vers VPS**

1. Containeriser le backend (Docker)
2. Déployer sur Fly.io ou Railway
3. Adapter le stockage (SQLite cloud ou Turso)
4. Gérer la sync des notes

Coût: ~$5-10/mois
Effort: 1-2 semaines

---

## Réponses aux Questions Clés

### "Python est-il le bon choix?"

**Oui.** Python avec FastAPI est parfaitement adapté:
- Async natif, très performant pour I/O
- Écosystème riche (Anthropic SDK, IMAP, etc.)
- Tu le maîtrises
- 50k lignes de code déjà écrit et fonctionnel

Un portage vers Go, Rust ou Node n'apporterait pas de gain significatif pour ton cas d'usage.

### "Terminal est-il le bon mode d'interaction?"

**Non pertinent** — tu utilises principalement la PWA web, pas le terminal.
Le CLI reste utile pour les tâches batch/automation, mais ce n'est pas ton interface principale.

### "Faut-il un serveur cloud?"

**Pas nécessairement.** Avec Tailscale, ton Mac devient accessible comme un serveur privé.
Le cloud n'est utile que si:
- Tu veux un accès 24/7 même Mac éteint
- Tu ne veux pas dépendre de ton Mac

### "Comment améliorer l'intégration iOS?"

**Capacitor** est la réponse. Il te donne:
- Push notifications iOS natives
- Haptics natifs
- App Store distribution possible
- Sans réécrire le frontend

---

## Verdict Final

**Garde l'architecture actuelle.** Elle est solide et bien conçue.

Les vrais quick wins sont:
1. **Tailscale** pour accès mobile (immédiat)
2. **Capacitor** pour iOS natif (si besoin notifications)
3. **VPS** seulement si disponibilité 24/7 devient critique

Pas besoin de tout réécrire. Scapin est déjà bien architecturé.

---

## Stack Technique Actuelle (Référence)

| Composant | Technologie | État |
|-----------|-------------|------|
| Backend | Python 3.11+ / FastAPI | Production (~50k lignes) |
| Frontend | SvelteKit 2.x / Svelte 5 | Production (PWA mobile-first) |
| CLI | Typer / Rich | Production |
| Stockage | JSON + SQLite + FAISS | Local-first |
| IA | Anthropic Claude API | Cloud (~$27/mois) |
| Intégrations | IMAP, MS Graph, iCloud, OmniFocus | Production |
