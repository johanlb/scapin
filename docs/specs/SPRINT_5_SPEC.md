# Sprint 5 : Qualité & Release — Spécification

**Date de création** : 9 janvier 2026
**Statut** : Planifié
**Objectif** : v1.0 Release Candidate
**Dépendance** : Sprint 4 ✅

---

## Résumé Exécutif

Le Sprint 5 est le dernier sprint avant la release v1.0. Il se concentre sur :
1. **Tests E2E** — Validation automatisée de tous les parcours utilisateur
2. **Performance** — Score Lighthouse > 90 sur toutes les métriques
3. **Documentation** — Guide utilisateur complet en français
4. **Audit Sécurité** — Vérification OWASP Top 10 et dépendances

### Critères de Release v1.0 RC

- [ ] Tests E2E passent (desktop + mobile)
- [ ] Lighthouse > 90 partout (Performance, Accessibility, Best Practices, SEO)
- [ ] Guide utilisateur complet disponible (Markdown + in-app)
- [ ] Zéro bug critique connu
- [ ] Audit sécurité validé

---

## 1. Tests E2E Playwright

### Décisions

| Aspect | Décision |
|--------|----------|
| **Couverture** | Toutes les pages |
| **Viewports** | Desktop (1280px) + Mobile (375px) |
| **Backend** | Backend réel local (pas de mock) |
| **Framework** | Playwright |

### Pages à Couvrir

| Page | Route | Scénarios |
|------|-------|-----------|
| **Login** | `/login` | Login PIN, erreur PIN, session expirée |
| **Briefing** | `/` | Affichage briefing, quick actions, conflits calendrier |
| **Flux** | `/flux` | Liste items, approbation, rejet, snooze, undo |
| **Flux Focus** | `/flux/focus` | Mode focus, navigation clavier, session complète |
| **Flux Détail** | `/flux/[id]` | Vue détail email, HTML sanitisé |
| **Notes** | `/notes` | Liste notes, arbre dossiers, sync Apple Notes |
| **Note Détail** | `/notes/[...path]` | Lecture, édition Markdown, historique, chat |
| **Notes Review** | `/notes/review` | Session révision SM-2, notation 0-5 |
| **Brouillons** | `/drafts` | Liste brouillons, édition, envoi |
| **Journal** | `/journal` | Multi-sources, questions, corrections |
| **Discussions** | `/discussions` | Liste sessions, nouveau chat, messages |
| **Teams** | `/teams/[chatId]` | Vue détail message Teams |
| **Stats** | `/stats` | Graphiques, tendances 7/30j |
| **Settings** | `/settings` | Tous les onglets, modifications |
| **Valets** | `/valets` | Dashboard valets, statuts |
| **Search** | `Cmd+K` | Recherche globale, navigation résultats |

### Structure des Tests

```
web/
├── playwright.config.ts          # Configuration Playwright
├── e2e/
│   ├── fixtures/
│   │   ├── auth.ts              # Fixture login
│   │   └── test-data.ts         # Données de test
│   ├── pages/
│   │   ├── login.spec.ts        # Tests page login
│   │   ├── briefing.spec.ts     # Tests page briefing
│   │   ├── flux.spec.ts         # Tests page flux
│   │   ├── flux-focus.spec.ts   # Tests mode focus
│   │   ├── notes.spec.ts        # Tests notes
│   │   ├── notes-review.spec.ts # Tests révision SM-2
│   │   ├── drafts.spec.ts       # Tests brouillons
│   │   ├── journal.spec.ts      # Tests journal
│   │   ├── discussions.spec.ts  # Tests discussions
│   │   ├── stats.spec.ts        # Tests stats
│   │   ├── settings.spec.ts     # Tests settings
│   │   └── valets.spec.ts       # Tests valets
│   ├── features/
│   │   ├── search.spec.ts       # Tests recherche globale
│   │   ├── keyboard.spec.ts     # Tests raccourcis clavier
│   │   ├── notifications.spec.ts # Tests notifications
│   │   └── responsive.spec.ts   # Tests mobile
│   └── flows/
│       ├── email-workflow.spec.ts    # Flux complet email
│       ├── note-enrichment.spec.ts   # Flux enrichissement notes
│       └── session-complete.spec.ts  # Session utilisateur complète
```

### Scénarios Critiques (Priorité 1)

#### 1. Workflow Email Complet
```gherkin
Feature: Email Processing Workflow

  Scenario: Traitement email de bout en bout
    Given je suis connecté
    And il y a des emails en attente
    When je vais sur la page Flux
    Then je vois la liste des emails à traiter
    When je clique sur un email
    Then je vois le détail de l'email
    When je clique sur "Approuver"
    Then l'email est déplacé vers "Approuvés"
    And un toast "Undo" apparaît pendant 5 secondes
    When je clique sur "Undo"
    Then l'email revient dans "En attente"
```

#### 2. Session Révision Notes
```gherkin
Feature: Note Review Session

  Scenario: Session de révision SM-2
    Given je suis connecté
    And il y a des notes à réviser
    When je vais sur /notes/review
    Then je vois la première note à réviser
    And je vois les boutons de notation (0-5)
    When j'appuie sur "4" (touche clavier)
    Then la note est notée avec qualité 4
    And je passe à la note suivante
    When toutes les notes sont révisées
    Then je vois "Session terminée"
    And je vois les stats de la session
```

#### 3. Recherche Globale
```gherkin
Feature: Global Search

  Scenario: Recherche et navigation
    Given je suis connecté
    When j'appuie sur Cmd+K
    Then la palette de commandes s'ouvre
    When je tape "projet alpha"
    Then je vois les résultats de recherche
    And les résultats sont groupés par type
    When je navigue avec les flèches et appuie Entrée
    Then je suis redirigé vers le résultat sélectionné
```

### Configuration Playwright

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    // Desktop
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // Mobile
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

  webServer: [
    {
      command: 'cd .. && python scapin.py serve',
      url: 'http://localhost:8000/api/health',
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
    },
  ],
});
```

### Fixtures

```typescript
// e2e/fixtures/auth.ts
import { test as base, Page } from '@playwright/test';

export const test = base.extend<{ authenticatedPage: Page }>({
  authenticatedPage: async ({ page }, use) => {
    // Login avec PIN
    await page.goto('/login');
    await page.click('[data-testid="pin-1"]');
    await page.click('[data-testid="pin-2"]');
    await page.click('[data-testid="pin-3"]');
    await page.click('[data-testid="pin-4"]');
    await page.waitForURL('/');
    await use(page);
  },
});
```

---

## 2. Performance Lighthouse

### Objectifs

| Métrique | Cible | Minimum |
|----------|-------|---------|
| **Performance** | > 90 | 85 |
| **Accessibility** | > 90 | 90 |
| **Best Practices** | > 90 | 85 |
| **SEO** | > 90 | 85 |

### Pages à Auditer

| Page | Priorité | Notes |
|------|----------|-------|
| `/` (Briefing) | Critique | Page d'accueil, doit être rapide |
| `/flux` | Critique | Liste potentiellement longue |
| `/notes` | Haute | Arbre de dossiers |
| `/login` | Haute | Première impression |
| `/stats` | Moyenne | Graphiques lourds |

### Optimisations Prévues

#### Performance
- [ ] Lazy loading des composants non-critiques
- [ ] Image optimization (format WebP, srcset)
- [ ] Bundle splitting par route
- [ ] Preload des fonts critiques
- [ ] Service Worker caching optimisé

#### Accessibility
- [ ] Vérification ARIA labels complets
- [ ] Contraste couleurs (WCAG AA)
- [ ] Focus visible sur tous les éléments interactifs
- [ ] Navigation clavier complète
- [ ] Skip links

#### Best Practices
- [ ] HTTPS partout
- [ ] Pas de console.log en production
- [ ] CSP headers configurés
- [ ] Source maps en production (optionnel)

#### SEO
- [ ] Meta tags complets
- [ ] robots.txt
- [ ] Structured data (JSON-LD) si applicable

### Script d'Audit

```bash
#!/bin/bash
# scripts/lighthouse-audit.sh

PAGES=("/" "/login" "/flux" "/notes" "/stats")
OUTPUT_DIR="lighthouse-reports"

mkdir -p $OUTPUT_DIR

for page in "${PAGES[@]}"; do
  filename=$(echo $page | tr '/' '-')
  [ -z "$filename" ] && filename="home"

  npx lighthouse "http://localhost:5173$page" \
    --output=html \
    --output-path="$OUTPUT_DIR/$filename.html" \
    --chrome-flags="--headless" \
    --preset=desktop

  echo "Audited $page → $OUTPUT_DIR/$filename.html"
done
```

---

## 3. Guide Utilisateur

### Format

| Aspect | Décision |
|--------|----------|
| **Source** | Markdown dans `/docs/user-guide/` |
| **Rendu** | Page `/help` in-app |
| **Langue** | Français uniquement |
| **Contenu** | Complet + Architecture |

### Structure du Guide

```
docs/user-guide/
├── index.md                    # Introduction
├── 01-installation.md          # Installation et configuration
├── 02-premiers-pas.md          # Démarrage rapide
├── 03-fonctionnalites/
│   ├── briefing.md            # Briefing du matin
│   ├── flux-email.md          # Traitement des emails
│   ├── notes.md               # Gestion des notes
│   ├── journal.md             # Journaling quotidien
│   ├── discussions.md         # Chat avec Scapin
│   ├── teams.md               # Intégration Teams
│   └── calendrier.md          # Intégration Calendrier
├── 04-raccourcis-clavier.md   # Tous les raccourcis
├── 05-troubleshooting.md      # Résolution de problèmes
├── 06-architecture/
│   ├── valets.md              # L'équipe des valets
│   └── flux-donnees.md        # Comment circulent les données
└── glossaire.md               # Termes et concepts
```

### Sections Détaillées

#### 1. Installation (01-installation.md)

- Prérequis système (Python 3.11+, Node.js 20+)
- Installation via pip/git
- Configuration initiale (.env)
- Configuration des intégrations :
  - Email (IMAP)
  - Microsoft Teams
  - Microsoft Calendar
  - Apple Notes
- Premier lancement
- Configuration du PIN

#### 2. Premiers Pas (02-premiers-pas.md)

- Connexion (PIN)
- Découverte du dashboard (Briefing)
- Traiter son premier email
- Créer sa première note
- Faire son premier journaling

#### 3. Fonctionnalités (03-fonctionnalites/)

Chaque fichier suit le format :
- **Présentation** — À quoi ça sert
- **Accès** — Comment y accéder (menu, raccourci)
- **Utilisation** — Guide pas à pas avec screenshots
- **Options** — Paramètres disponibles
- **Astuces** — Tips & tricks

#### 4. Raccourcis Clavier (04-raccourcis-clavier.md)

| Raccourci | Action | Contexte |
|-----------|--------|----------|
| `Cmd+K` | Recherche globale | Global |
| `J` / `K` | Item suivant/précédent | Listes |
| `A` | Approuver | Flux |
| `R` | Rejeter | Flux |
| `S` | Snooze | Flux |
| `E` | Éditer | Item sélectionné |
| `Enter` | Ouvrir détail | Item sélectionné |
| `Escape` | Fermer/Retour | Modal, panel |
| `?` | Aide raccourcis | Global |
| `1-6` | Noter (révision) | Notes Review |

#### 5. Troubleshooting (05-troubleshooting.md)

- Problèmes de connexion
- Emails non synchronisés
- Teams/Calendar non connecté
- Notes non sauvegardées
- Performance lente
- Logs et diagnostic

#### 6. Architecture (06-architecture/)

**valets.md** — L'équipe des valets
- Trivelin : La perception
- Sancho : Le raisonnement
- Passepartout : La mémoire
- Planchet : La planification
- Figaro : L'exécution
- Sganarelle : L'apprentissage
- Jeeves : L'interface

**flux-donnees.md** — Le flux cognitif
- Email → Analyse → Action
- Notes ↔ Enrichissement bidirectionnel
- Révision espacée SM-2
- Boucle de feedback

### Page /help In-App

```svelte
<!-- web/src/routes/help/+page.svelte -->
<script lang="ts">
  import { marked } from 'marked';
  import { page } from '$app/stores';

  // Charger le contenu Markdown dynamiquement
  let content = '';
  let section = $page.url.searchParams.get('section') || 'index';

  $effect(() => {
    loadContent(section);
  });

  async function loadContent(s: string) {
    const res = await fetch(`/api/docs/${s}`);
    const md = await res.text();
    content = marked(md);
  }
</script>

<div class="help-page">
  <nav class="help-nav">
    <!-- Navigation latérale -->
  </nav>
  <article class="help-content prose">
    {@html content}
  </article>
</div>
```

---

## 4. Audit Sécurité

### Scope

| Catégorie | Items à Vérifier |
|-----------|------------------|
| **OWASP Top 10** | Injection, XSS, CSRF, etc. |
| **Dépendances** | Vulnérabilités connues (pip-audit, npm audit) |
| **Secrets** | Aucun secret hardcodé |
| **Permissions** | Principe du moindre privilège |
| **Auth** | JWT sécurisé, expiration, refresh |

### Checklist OWASP Top 10 (2021)

- [ ] **A01:2021 – Broken Access Control**
  - Vérifier les autorisations sur chaque endpoint
  - Tester l'accès sans authentification
  - Tester l'accès avec token expiré

- [ ] **A02:2021 – Cryptographic Failures**
  - JWT avec secret fort (32+ chars)
  - Pas de stockage de secrets en clair
  - HTTPS enforced

- [ ] **A03:2021 – Injection**
  - SQL injection (parameterized queries)
  - Command injection (subprocess)
  - Path traversal (note paths)

- [ ] **A04:2021 – Insecure Design**
  - Rate limiting sur login
  - Validation des entrées

- [ ] **A05:2021 – Security Misconfiguration**
  - CORS configuré correctement
  - Headers de sécurité (CSP, X-Frame-Options)
  - Pas de debug en production

- [ ] **A06:2021 – Vulnerable Components**
  - pip-audit clean
  - npm audit clean

- [ ] **A07:2021 – Auth Failures**
  - Brute-force protection (rate limiting)
  - Session timeout
  - Secure cookie flags

- [ ] **A08:2021 – Software/Data Integrity**
  - Vérification des updates
  - Intégrité des données

- [ ] **A09:2021 – Logging/Monitoring**
  - Logs des événements de sécurité
  - Pas de données sensibles dans les logs

- [ ] **A10:2021 – SSRF**
  - Validation des URLs externes

### Commandes d'Audit

```bash
# Backend Python
pip-audit
bandit -r src/

# Frontend Node.js
cd web && npm audit

# Secrets
gitleaks detect --source . --verbose
```

### Rapport de Sécurité

Le rapport final doit inclure :
1. Résumé exécutif
2. Vulnérabilités trouvées (CRITICAL/HIGH/MEDIUM/LOW)
3. Recommandations
4. Preuves de correction

---

## 5. Ordre d'Exécution

```
1. Tests E2E Playwright
   ├── Setup Playwright (config, fixtures)
   ├── Tests pages (login → briefing → flux → notes → ...)
   ├── Tests features (search, keyboard, notifications)
   └── Tests flows (email workflow, note enrichment)

2. Lighthouse > 90
   ├── Audit initial (baseline)
   ├── Optimisations Performance
   ├── Optimisations Accessibility
   ├── Optimisations Best Practices
   └── Audit final (validation > 90)

3. Guide Utilisateur
   ├── Structure des fichiers
   ├── Rédaction sections
   ├── Page /help in-app
   └── Relecture et corrections

4. Audit Sécurité
   ├── OWASP Top 10 checklist
   ├── pip-audit + npm audit
   ├── bandit + gitleaks
   └── Rapport final
```

---

## 6. Livrables

| Item | Fichiers | Critère de Succès |
|------|----------|-------------------|
| **Tests E2E** | `web/e2e/**/*.spec.ts` | 100% des pages couvertes, CI green |
| **Lighthouse** | `lighthouse-reports/` | Score > 90 sur toutes les métriques |
| **Guide** | `docs/user-guide/**/*.md` | 7 sections complètes |
| **Page /help** | `web/src/routes/help/` | Navigation fluide, contenu chargé |
| **Audit** | `docs/security/audit-v1.0.md` | Zéro CRITICAL/HIGH non résolu |

---

## 7. Estimation

| Item | Effort |
|------|--------|
| Tests E2E (setup + 15 pages) | ~8h |
| Lighthouse optimisations | ~4h |
| Guide utilisateur | ~6h |
| Page /help in-app | ~2h |
| Audit sécurité | ~3h |
| **Total** | **~23h** |

---

## 8. Risques et Mitigations

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Backend instable pour E2E | Tests flaky | Fixtures robustes, retries |
| Score Lighthouse difficile | Blocage release | Objectif minimum 85 |
| Rédaction guide longue | Retard | Sections prioritaires d'abord |
| Vulnérabilités découvertes | Blocage | Correction immédiate CRITICAL |

---

**Document créé le** : 9 janvier 2026
**Auteur** : Claude Code
**Statut** : Approuvé pour exécution
