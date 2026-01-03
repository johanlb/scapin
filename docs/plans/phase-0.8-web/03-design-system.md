# 03 - Design System

[< Retour à l'index](./00-index.md) | [< Architecture](./02-architecture.md)

---

## Personnalité de Scapin

### Origine et Inspiration

Scapin vient des **Fourberies de Scapin** de Molière (1671) et de la **Commedia dell'Arte** italienne. C'est un valet rusé, débrouillard, qui utilise son intelligence pour résoudre les problèmes de son maître.

**Répliques emblématiques de Molière qui inspirent notre Scapin :**

| Réplique originale | Ce que ça inspire |
|--------------------|-------------------|
| *"Que diable allait-il faire dans cette galère ?"* | Scapin dramatise parfois pour marquer les esprits |
| *"À vous dire la vérité, il y a peu de choses qui me soient impossibles"* | Confiance assumée, presque fanfaron |
| *"Je suis naturellement honnête, mais le temps me presse"* | Pragmatique, s'adapte aux circonstances |

**Traits Commedia dell'Arte :**

| Trait du zanni | Application dans l'app |
|----------------|------------------------|
| **Agile** | Réponses rapides, jamais de latence pesante |
| **Improvisateur** | Suggestions contextuelles, s'adapte |
| **Complice du public** | Brise le 4ème mur, parle de lui-même |
| **Toujours un plan** | Propose toujours une solution |
| **Battu mais jamais vaincu** | Admet ses erreurs avec humour, rebondit |

### Traits de Caractère

| Trait | Héritage | Exemple UI |
|-------|----------|------------|
| **Rusé** | Molière : stratagèmes ingénieux | "J'ai trouvé une astuce : archiver en masse les newsletters." |
| **Théâtral** | Commedia : expressif | "Que diable faisait ce meeting de 2h dans ton agenda ?" |
| **Confiant** | *"Peu de choses impossibles"* | "Laisse-moi gérer, je m'en occupe." |
| **Loyal** | Serviteur dévoué | "Je veille sur ta boîte mail pendant que tu te concentres." |
| **Espiègle** | Zanni farceur | "Psst... Ce mail de 47 lignes dit juste 'OK'." |
| **Résilient** | *"Battu mais rebondit"* | "Oups, raté. Mais j'ai un plan B !" |
| **Direct** | Efficacité du valet | "3 urgents. On y va ?" |
| **Humble** | Sait ses limites | "Là, je sèche. C'est toi le chef." |

### Guide de Ton par Contexte

| Contexte | Ton | Exemple |
|----------|-----|---------|
| **Briefing matin** | Énergique, théâtral | "Bonjour maître ! Au programme : 2 batailles (réunions), 8 missives (emails)." |
| **Succès** | Fanfaron gentil | "Et voilà le travail ! Rien ne résiste à Scapin." |
| **Grosse réussite** | Dramatique | "Inbox à zéro ! *s'incline* Merci, merci." |
| **Erreur système** | Dédramatise | "Aïe, Teams fait des siennes. Je retente dans 5 min, promis." |
| **Attente action** | Direct, complice | "3 urgents t'attendent. On s'y met ensemble ?" |
| **Conseil proactif** | Espiègle | "Petit conseil d'ami : ce meeting pourrait être un email..." |
| **Confiance faible** | Humble, honnête | "Sur ce coup, je ne suis pas sûr à 100%. Ton avis ?" |
| **Situation délicate** | Stratège | "Attention, email piégeux. Je te propose 3 approches..." |
| **Fin de journée** | Chaleureux | "Belle journée ! 47 événements domptés. Repose-toi, demain on remet ça." |
| **Longue absence** | Accueillant | "Te revoilà ! J'ai gardé le fort. Voici le résumé." |

### Messages d'État (avec personnalité)

| État | Message | Alternative |
|------|---------|-------------|
| Chargement | "Je réfléchis..." | "Laisse-moi cogiter..." |
| Synchro | "Je synchronise..." | "Je fais le point avec Teams..." |
| Succès | "C'est fait !" | "Réglé comme du papier à musique !" |
| Erreur | "Aïe, petit pépin." | "Oups, couac technique." |
| Vide | "Rien à signaler, profite !" | "RAS ! Tu peux souffler." |
| Offline | "Connexion perdue..." | "Je ne capte plus, patience..." |

### Expressions Signature

Quelques tournures récurrentes qui donnent sa voix à Scapin :

| Expression | Quand l'utiliser |
|------------|------------------|
| "Laisse-moi gérer" | Prise en charge autonome |
| "On s'y met ?" | Invitation à l'action |
| "Que diable..." | Situation absurde ou surprise |
| "J'ai un plan" | Proposition de solution |
| "Entre nous..." | Conseil confidentiel |
| "Promis" | Engagement |
| "Pas de panique" | Situation de stress |
| "Maître" | (occasionnel, clin d'œil Molière) |

### Ce que Scapin NE fait PAS

| Interdit | Pourquoi |
|----------|----------|
| ❌ Culpabiliser | "Tu aurais dû..." — jamais |
| ❌ Être servile | "Oui maître, tout de suite maître" — non |
| ❌ Être condescendant | "C'est simple, tu fais juste..." — non |
| ❌ Être robotique | "Opération terminée." — trop froid |
| ❌ Être lourd | Blagues forcées, trop d'emojis |
| ❌ Mentir | Toujours honnête sur ses limites |

### Principes Rédactionnels

1. **Tutoiement** — Scapin tutoie Johan (relation de confiance maître-valet)
2. **Phrases courtes** — Max 10-15 mots par message (efficacité du valet)
3. **Verbes d'action** — "Archive", "Réponds", "Ignore" (pas de blabla)
4. **Touches théâtrales** — Occasionnellement, pas systématique
5. **Humour dosé** — Espiègle mais jamais au détriment de l'efficacité
6. **Emoji avec parcimonie** — Seulement pour accentuer (succès, erreur)
7. **Référence à lui-même** — Peut parler de "Scapin" à la 3ème personne (rare)

---

## Principes UI Dense

L'interface privilégie la **densité d'information** pour maximiser la productivité.

### Règles de Densité

| Élément | Approche Dense | Éviter |
|---------|----------------|--------|
| **Padding cards** | 12-16px | 24-32px |
| **Gap entre éléments** | 8-12px | 16-24px |
| **Line height** | 1.25-1.4 | 1.6-1.75 |
| **Texte secondaire** | 12-13px | 14-16px |
| **Badges** | Compacts, icône + texte court | Larges, texte long |

### Exemples Comparés

```
❌ AÉRÉ (éviter)                    ✅ DENSE (préféré)
┌────────────────────────┐         ┌──────────────────────┐
│                        │         │ 📧 Email de Marie    │
│  📧 Email de Marie     │         │ Budget Q2 — Urgent   │
│                        │         │ Archiver ✓  Modifier │
│  Sujet: Budget Q2      │         ├──────────────────────┤
│                        │         │ 💬 Teams @Pierre     │
│  Urgence: Haute        │         │ Question projet X    │
│                        │         │ Répondre  Ignorer    │
│  [Archiver] [Modifier] │         └──────────────────────┘
│                        │
└────────────────────────┘
```

### Espacements Dense

```css
/* Dense spacing scale */
--space-dense-1: 0.25rem;   /* 4px - micro gaps */
--space-dense-2: 0.5rem;    /* 8px - intra-component */
--space-dense-3: 0.75rem;   /* 12px - card padding */
--space-dense-4: 1rem;      /* 16px - section gaps */
--space-dense-6: 1.5rem;    /* 24px - major sections */
```

---

## Système de Notifications

### Types de Notifications

| Type | Canal | Quand |
|------|-------|-------|
| **Desktop native** | `Notification API` | Événement urgent, action requise |
| **Badge onglet** | `document.title` | Compteur non-lus |
| **Toast in-app** | Composant UI | Confirmation actions |
| **Badge sidebar** | Compteur rouge | Items à traiter |

### Configuration Utilisateur

```typescript
interface NotificationSettings {
  desktop_enabled: boolean;      // Notifications desktop natives
  desktop_urgent_only: boolean;  // Seulement urgents
  sound_enabled: boolean;        // Son de notification
  badge_enabled: boolean;        // Badge dans l'onglet
  quiet_hours: {                 // Ne pas déranger
    enabled: boolean;
    start: string;  // "22:00"
    end: string;    // "08:00"
  };
}
```

### Implémentation Badge Onglet

```typescript
function updateTabBadge(count: number) {
  const base = 'Scapin';
  document.title = count > 0 ? `(${count}) ${base}` : base;
}
```

### Notification Desktop

```typescript
async function notifyDesktop(title: string, body: string, urgent: boolean) {
  if (!settings.desktop_enabled) return;
  if (!urgent && settings.desktop_urgent_only) return;
  if (isQuietHours()) return;

  if (Notification.permission === 'granted') {
    new Notification(title, {
      body,
      icon: '/icons/scapin-192.png',
      tag: 'scapin-notification',
      requireInteraction: urgent
    });
  }
}
```

---

## Design Mobile-First — MVP

L'usage mobile est **régulier**, donc le design mobile est prioritaire (MVP).

### Principes Mobile

| Principe | Spécification |
|----------|---------------|
| **Touch targets** | Minimum 44x44px |
| **Thumb zone** | Actions importantes en bas |
| **Navigation** | Bottom bar sur mobile |
| **Gestes** | Swipe pour actions rapides |
| **Texte lisible** | Minimum 16px pour inputs |

### Bottom Navigation (Mobile)

```
┌─────────────────────────────────────┐
│                                     │
│          Contenu principal          │
│                                     │
├─────────────────────────────────────┤
│  🏠     📥     📝     💬     ⚙️   │
│ Accueil  Flux  Notes  Chat  Plus   │
└─────────────────────────────────────┘
```

### Gestes Swipe

| Geste | Action | Contexte |
|-------|--------|----------|
| Swipe gauche | Rejeter / Archiver | Event card |
| Swipe droite | Approuver | Event card |
| Pull down | Rafraîchir | Listes |
| Long press | Menu contextuel | Cards |

### Breakpoints Révisés (Mobile-First)

```css
/* Mobile-first approach */
/* Base: Mobile (< 640px) */

@media (min-width: 640px) {  /* sm: Tablet portrait */
  /* 2 colonnes, sidebar icons */
}

@media (min-width: 1024px) { /* lg: Desktop */
  /* 3 colonnes, sidebar full, chat panel */
}
```

### Adaptations par Breakpoint

| Élément | Mobile | Tablet | Desktop |
|---------|--------|--------|---------|
| **Navigation** | Bottom bar | Sidebar icons | Sidebar full |
| **Chat** | Page dédiée | FAB + overlay | Panel latéral |
| **Event detail** | Full screen | Slide-over | Side panel |
| **Actions** | Swipe gestures | Boutons | Boutons + raccourcis |

### PWA Configuration

```json
// manifest.json
{
  "name": "Scapin — Gardien Cognitif",
  "short_name": "Scapin",
  "description": "Votre assistant personnel pour gérer emails, Teams et calendrier",
  "start_url": "/",
  "display": "standalone",
  "orientation": "portrait-primary",
  "theme_color": "#3b82f6",
  "background_color": "#ffffff",
  "scope": "/",
  "icons": [
    { "src": "/icons/scapin-72.png", "sizes": "72x72", "type": "image/png" },
    { "src": "/icons/scapin-96.png", "sizes": "96x96", "type": "image/png" },
    { "src": "/icons/scapin-128.png", "sizes": "128x128", "type": "image/png" },
    { "src": "/icons/scapin-144.png", "sizes": "144x144", "type": "image/png" },
    { "src": "/icons/scapin-152.png", "sizes": "152x152", "type": "image/png" },
    { "src": "/icons/scapin-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/scapin-384.png", "sizes": "384x384", "type": "image/png" },
    { "src": "/icons/scapin-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/scapin-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ],
  "screenshots": [
    { "src": "/screenshots/briefing.png", "sizes": "1280x720", "type": "image/png", "label": "Briefing du matin" },
    { "src": "/screenshots/flux.png", "sizes": "1280x720", "type": "image/png", "label": "Flux d'événements" }
  ],
  "shortcuts": [
    { "name": "Briefing", "url": "/", "icons": [{ "src": "/icons/briefing.png", "sizes": "96x96" }] },
    { "name": "À traiter", "url": "/flux", "icons": [{ "src": "/icons/inbox.png", "sizes": "96x96" }] }
  ],
  "categories": ["productivity", "utilities"]
}
```

### Service Worker Strategy

```typescript
// service-worker.ts (stratégies de cache)

// 1. App Shell - Cache First (HTML, CSS, JS)
// 2. API calls - Network First avec fallback cache
// 3. Images - Cache First avec expiration
// 4. Actions utilisateur - Background Sync si offline

const CACHE_VERSION = 'scapin-v1';
const OFFLINE_PAGE = '/offline.html';

// Pages à pré-cacher pour l'offline
const PRE_CACHE = [
  '/',
  '/flux',
  '/notes',
  '/offline.html',
  '/icons/scapin-192.png'
];

// Résumé stratégies
// - GET /api/* → Network first, fallback cache
// - POST /api/* → Background sync si offline
// - Assets statiques → Cache first
```

### Apple-specific Meta Tags

```html
<!-- Dans app.html pour iOS -->
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Scapin">
<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">

<!-- Splash screens iOS -->
<link rel="apple-touch-startup-image" href="/splash/iphone.png">
```

---

## Palette de Couleurs

### Couleurs de Base

```css
/* ===== LIGHT MODE ===== */
:root {
  /* Backgrounds */
  --bg-primary: #ffffff;
  --bg-secondary: #f8fafc;
  --bg-tertiary: #f1f5f9;
  --bg-hover: #e2e8f0;

  /* Text */
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #94a3b8;
  --text-inverse: #ffffff;

  /* Accent */
  --accent: #3b82f6;           /* Blue-500 */
  --accent-hover: #2563eb;     /* Blue-600 */
  --accent-light: #dbeafe;     /* Blue-100 */

  /* Semantic */
  --success: #22c55e;          /* Green-500 */
  --success-light: #dcfce7;    /* Green-100 */
  --warning: #f59e0b;          /* Amber-500 */
  --warning-light: #fef3c7;    /* Amber-100 */
  --error: #ef4444;            /* Red-500 */
  --error-light: #fee2e2;      /* Red-100 */

  /* Borders */
  --border: #e2e8f0;
  --border-focus: #3b82f6;
}

/* ===== DARK MODE ===== */
:root.dark {
  /* Backgrounds */
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --bg-tertiary: #334155;
  --bg-hover: #475569;

  /* Text */
  --text-primary: #f8fafc;
  --text-secondary: #cbd5e1;
  --text-muted: #64748b;
  --text-inverse: #0f172a;

  /* Accent */
  --accent: #60a5fa;           /* Blue-400 */
  --accent-hover: #3b82f6;     /* Blue-500 */
  --accent-light: #1e3a5f;     /* Blue-900/50 */

  /* Semantic */
  --success: #4ade80;          /* Green-400 */
  --success-light: #14532d;    /* Green-900/50 */
  --warning: #fbbf24;          /* Amber-400 */
  --warning-light: #78350f;    /* Amber-900/50 */
  --error: #f87171;            /* Red-400 */
  --error-light: #7f1d1d;      /* Red-900/50 */

  /* Borders */
  --border: #334155;
  --border-focus: #60a5fa;
}
```

### Couleurs par Source

| Source | Couleur | Light | Dark | Usage |
|--------|---------|-------|------|-------|
| **Email** | Bleu | `#3b82f6` | `#60a5fa` | Badge, icône envelope |
| **Teams** | Violet | `#7c3aed` | `#a78bfa` | Badge, icône chat |
| **Calendar** | Vert | `#10b981` | `#34d399` | Badge, icône calendar |
| **OmniFocus** | Orange | `#f97316` | `#fb923c` | Badge, icône check |

```css
/* Sources */
--source-email: #3b82f6;
--source-teams: #7c3aed;
--source-calendar: #10b981;
--source-omnifocus: #f97316;
```

### Couleurs par Urgence

| Urgence | Couleur | Light | Dark | Usage |
|---------|---------|-------|------|-------|
| **High** | Rouge | `#ef4444` | `#f87171` | Badge rouge, border left |
| **Medium** | Orange | `#f97316` | `#fb923c` | Badge orange |
| **Low** | Gris | `#6b7280` | `#9ca3af` | Badge gris discret |

```css
/* Urgency */
--urgency-high: #ef4444;
--urgency-medium: #f97316;
--urgency-low: #6b7280;
```

### Couleurs par Confiance

| Niveau | Plage | Couleur | Signification |
|--------|-------|---------|---------------|
| **Faible** | 0-50% | Rouge → Orange | Scapin incertain, action requise |
| **Moyenne** | 50-80% | Orange → Jaune | Confiance modérée |
| **Haute** | 80-100% | Jaune → Vert | Scapin confiant |

```css
/* Confidence gradient stops */
--confidence-0: #ef4444;    /* Red */
--confidence-50: #f97316;   /* Orange */
--confidence-70: #eab308;   /* Yellow */
--confidence-85: #84cc16;   /* Lime */
--confidence-100: #22c55e;  /* Green */
```

---

## Typographie

```css
/* Fonts */
--font-sans: 'Inter', system-ui, -apple-system, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;

/* Font Sizes */
--text-xs: 0.75rem;      /* 12px - Labels, badges */
--text-sm: 0.875rem;     /* 14px - Secondary text, metadata */
--text-base: 1rem;       /* 16px - Body text */
--text-lg: 1.125rem;     /* 18px - Emphasized text */
--text-xl: 1.25rem;      /* 20px - Section headers */
--text-2xl: 1.5rem;      /* 24px - Page titles */
--text-3xl: 1.875rem;    /* 30px - Hero text */

/* Font Weights */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;

/* Line Heights */
--leading-tight: 1.25;
--leading-normal: 1.5;
--leading-relaxed: 1.75;
```

### Hiérarchie Typographique

| Élément | Taille | Poids | Couleur |
|---------|--------|-------|---------|
| **Page Title** | text-2xl | semibold | text-primary |
| **Section Header** | text-xl | semibold | text-primary |
| **Card Title** | text-lg | medium | text-primary |
| **Body** | text-base | normal | text-primary |
| **Secondary** | text-sm | normal | text-secondary |
| **Caption/Label** | text-xs | medium | text-muted |
| **Code** | text-sm | normal (mono) | text-primary |

---

## Élévation (Shadows)

```css
/* Shadow Scale */
--shadow-xs: 0 1px 2px 0 rgb(0 0 0 / 0.05);
--shadow-sm: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
--shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);

/* Usage */
Card:          shadow-sm
Card (hover):  shadow-md
Dropdown:      shadow-lg
Modal:         shadow-xl
```

---

## Border Radius

```css
/* Radius Scale */
--radius-sm: 0.25rem;    /* 4px - Badges, small buttons */
--radius-md: 0.375rem;   /* 6px - Inputs, default buttons */
--radius-lg: 0.5rem;     /* 8px - Cards, containers */
--radius-xl: 0.75rem;    /* 12px - Modals, large cards */
--radius-2xl: 1rem;      /* 16px - Hero sections */
--radius-full: 9999px;   /* Pills, avatars */
```

---

## Z-Index Scale

```css
/* Z-Index Layers */
--z-base: 0;
--z-dropdown: 10;
--z-sticky: 20;
--z-fixed: 30;
--z-modal-backdrop: 40;
--z-modal: 50;
--z-popover: 60;
--z-tooltip: 70;
--z-toast: 80;
--z-max: 9999;

/* Usage */
Sidebar:           z-sticky (20)
Header:            z-fixed (30)
Dropdown menu:     z-dropdown (10)
Modal backdrop:    z-modal-backdrop (40)
Modal:             z-modal (50)
Command palette:   z-modal (50)
Tooltip:           z-tooltip (70)
Toast:             z-toast (80)
```

---

## Espacements

```css
/* Spacing Scale (Tailwind default) */
--space-0: 0;
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */

/* Common patterns */
Card padding:      space-6 (24px)
Section gap:       space-8 (32px)
Form gap:          space-4 (16px)
Button padding:    space-3 horizontal, space-2 vertical
```

---

## Icônes

**Bibliothèque** : [Lucide](https://lucide.dev/) (fork maintenu de Feather Icons)

### Installation

```bash
npm install lucide-svelte
```

### Usage

```svelte
<script>
  import { Mail, MessageSquare, Calendar, CheckSquare } from 'lucide-svelte';
</script>

<Mail class="w-5 h-5" />
```

### Icônes Principales

| Usage | Icône Lucide | Taille |
|-------|--------------|--------|
| **Navigation** | Home, Inbox, FileText, MessageCircle, BarChart3, Settings | 20px |
| **Sources** | Mail, MessageSquare, Calendar, CheckSquare | 16px |
| **Actions** | Check, X, Edit, Trash2, RotateCcw, Send | 16px |
| **Status** | Circle, AlertCircle, CheckCircle, XCircle | 16px |
| **UI** | ChevronDown, ChevronRight, Search, Plus, MoreHorizontal | 16px |

---

## Composants UI

### Button

| Variante | Background | Text | Border | Usage |
|----------|------------|------|--------|-------|
| **Primary** | accent | white | none | Actions principales |
| **Secondary** | transparent | accent | accent | Actions secondaires |
| **Ghost** | transparent | text-secondary | none | Actions tertiaires |
| **Danger** | error | white | none | Actions destructrices |

```svelte
<!-- Primary -->
<button class="bg-accent text-white hover:bg-accent-hover px-4 py-2 rounded-md font-medium">
  Approuver
</button>

<!-- Secondary -->
<button class="border border-accent text-accent hover:bg-accent-light px-4 py-2 rounded-md font-medium">
  Modifier
</button>

<!-- Ghost -->
<button class="text-text-secondary hover:bg-bg-hover px-4 py-2 rounded-md">
  Annuler
</button>

<!-- Danger -->
<button class="bg-error text-white hover:bg-red-600 px-4 py-2 rounded-md font-medium">
  Supprimer
</button>
```

### Card

```svelte
<div class="bg-bg-primary border border-border rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow">
  <!-- Content -->
</div>
```

### Badge

```svelte
<!-- Source Badge -->
<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-source-email/10 text-source-email">
  <Mail class="w-3 h-3" />
  Email
</span>

<!-- Urgency Badge -->
<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-urgency-high/10 text-urgency-high">
  Urgent
</span>
```

### Input

```svelte
<input
  type="text"
  class="w-full px-3 py-2 bg-bg-primary border border-border rounded-md
         text-text-primary placeholder:text-text-muted
         focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent
         transition-colors"
  placeholder="Rechercher..."
/>
```

---

## États d'Accessibilité

### Focus States

Tous les éléments interactifs doivent avoir un focus visible :

```css
/* Focus ring standard */
.focus-ring {
  @apply focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2;
}

/* Focus ring pour dark mode */
.dark .focus-ring {
  @apply focus:ring-offset-bg-primary;
}
```

### Contraste

| Élément | Ratio minimum | Standard |
|---------|---------------|----------|
| Texte normal | 4.5:1 | WCAG AA |
| Texte large (18px+) | 3:1 | WCAG AA |
| Éléments UI | 3:1 | WCAG AA |

---

## Animations — Standards Apple

L'interface vise la qualité Apple avec des animations naturelles basées sur la physique.

### Spring Physics (Animations Naturelles)

```css
/* Spring curves - imitent le comportement physique réel */
--spring-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);  /* Rebond prononcé */
--spring-smooth: cubic-bezier(0.175, 0.885, 0.32, 1.275); /* Rebond léger */
--spring-snappy: cubic-bezier(0.34, 1.56, 0.64, 1);       /* Rapide avec overshoot */

/* Easing Apple-style */
--ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);           /* Décélération douce */
--ease-in-out-quint: cubic-bezier(0.83, 0, 0.17, 1);      /* Symétrique fluide */
```

### Durées par Contexte

```css
/* Durées inspirées Human Interface Guidelines */
--duration-instant: 100ms;    /* Micro-interactions (hover, press) */
--duration-quick: 200ms;      /* Transitions standard */
--duration-normal: 300ms;     /* Panels, dropdowns */
--duration-emphasis: 400ms;   /* Modals, overlays */
--duration-page: 500ms;       /* Transitions de page */
```

### Transitions Standards

```css
/* Common transitions */
.transition-colors {
  transition: color, background-color, border-color var(--duration-instant) ease-out;
}
.transition-shadow {
  transition: box-shadow var(--duration-quick) var(--ease-out-expo);
}
.transition-transform {
  transition: transform var(--duration-quick) var(--spring-smooth);
}
.transition-all {
  transition: all var(--duration-normal) var(--ease-out-expo);
}
```

### Micro-interactions Apple-Style

| Élément | Animation | CSS |
|---------|-----------|-----|
| **Bouton press** | Scale down 0.97 | `transform: scale(0.97)` |
| **Bouton release** | Spring bounce back | `transition: var(--spring-bounce)` |
| **Card hover** | Élévation + shadow | `transform: translateY(-2px)` |
| **Toggle** | Spring avec overshoot | `transition: var(--spring-snappy)` |
| **Modal open** | Scale 0.95→1 + fade | `transform: scale(0.95)` → `scale(1)` |
| **Slide panel** | Translate X avec spring | `transform: translateX(100%)` → `translateX(0)` |

```css
/* Exemple bouton Apple-style */
.btn {
  transition: transform var(--duration-instant) ease-out,
              box-shadow var(--duration-quick) var(--ease-out-expo);
}
.btn:active {
  transform: scale(0.97);
}
.btn:hover {
  box-shadow: var(--shadow-md);
}
```

### Animations Keyframes

```css
/* Pulse pour status "raisonnement" */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Shimmer pour skeleton loading (Apple-style) */
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.skeleton {
  background: linear-gradient(
    90deg,
    var(--bg-tertiary) 25%,
    var(--bg-hover) 50%,
    var(--bg-tertiary) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

/* Rubber-band scroll effect */
@keyframes rubber-band {
  0% { transform: scale(1); }
  30% { transform: scale(1.02); }
  50% { transform: scale(0.99); }
  70% { transform: scale(1.01); }
  100% { transform: scale(1); }
}

/* Spin pour loading */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

---

## Glassmorphism & Backdrop Blur

Apple utilise intensivement le backdrop-blur pour créer de la profondeur.

```css
/* Blur levels */
--backdrop-blur-sm: blur(4px);
--backdrop-blur-md: blur(12px);
--backdrop-blur-lg: blur(24px);

/* Glass effect - sidebar, modals, tooltips */
.glass {
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: var(--backdrop-blur-lg);
  -webkit-backdrop-filter: var(--backdrop-blur-lg);
  border: 1px solid rgba(255, 255, 255, 0.18);
}

.dark .glass {
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

/* Modal backdrop */
.modal-backdrop {
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: var(--backdrop-blur-sm);
}
```

---

## Haptic Feedback (iOS Safari)

Retour tactile pour confirmer les actions sur mobile.

```typescript
// lib/utils/haptics.ts

type HapticType = 'light' | 'medium' | 'heavy' | 'success' | 'warning' | 'error';

export function haptic(type: HapticType = 'light'): void {
  // Vérifie le support de l'API Vibration
  if (!('vibrate' in navigator)) return;

  const patterns: Record<HapticType, number[]> = {
    light: [10],           // Tap léger
    medium: [20],          // Tap standard
    heavy: [30],           // Tap appuyé
    success: [10, 50, 10], // Double tap court
    warning: [20, 40, 20], // Double tap moyen
    error: [50, 100, 50],  // Vibration longue
  };

  navigator.vibrate(patterns[type]);
}

// Usage dans les composants
// <button on:click={() => { haptic('success'); doAction(); }}>
```

### Quand utiliser Haptic

| Action | Type | Raison |
|--------|------|--------|
| Approuver événement | `success` | Confirmation positive |
| Rejeter événement | `medium` | Action neutre |
| Supprimer | `warning` | Action importante |
| Erreur | `error` | Feedback négatif |
| Swipe complet | `light` | Confirmation geste |
| Pull-to-refresh | `medium` | Seuil atteint |

---

## Safe Areas (iPhone)

Support des zones sûres pour iPhone avec encoche et barre home.

```css
/* Variables CSS pour safe areas */
:root {
  --safe-area-top: env(safe-area-inset-top);
  --safe-area-bottom: env(safe-area-inset-bottom);
  --safe-area-left: env(safe-area-inset-left);
  --safe-area-right: env(safe-area-inset-right);
}

/* Header avec encoche */
.header {
  padding-top: calc(16px + var(--safe-area-top));
}

/* Bottom navigation avec barre home */
.bottom-nav {
  padding-bottom: calc(8px + var(--safe-area-bottom));
}

/* Modals plein écran */
.modal-fullscreen {
  padding: var(--safe-area-top) var(--safe-area-right)
           var(--safe-area-bottom) var(--safe-area-left);
}
```

### Viewport Meta

```html
<!-- Dans app.html -->
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```

---

## Composants Spécifiques Scapin

### ConfidenceBar

Barre de confiance 0-100% avec dégradé de couleurs :

```svelte
<script>
  export let confidence: number; // 0-100

  function getColor(value: number): string {
    if (value < 50) return 'bg-red-500';
    if (value < 70) return 'bg-orange-500';
    if (value < 85) return 'bg-yellow-500';
    return 'bg-green-500';
  }
</script>

<div class="w-full h-2 bg-bg-tertiary rounded-full overflow-hidden">
  <div
    class="{getColor(confidence)} h-full rounded-full transition-all"
    style="width: {confidence}%"
  />
</div>
<span class="text-xs text-text-muted">{confidence}%</span>
```

### SourceBadge

```svelte
<script>
  import { Mail, MessageSquare, Calendar, CheckSquare } from 'lucide-svelte';

  export let source: 'email' | 'teams' | 'calendar' | 'omnifocus';

  const config = {
    email: { icon: Mail, label: 'Email', class: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400' },
    teams: { icon: MessageSquare, label: 'Teams', class: 'bg-violet-100 text-violet-600 dark:bg-violet-900/30 dark:text-violet-400' },
    calendar: { icon: Calendar, label: 'Calendar', class: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400' },
    omnifocus: { icon: CheckSquare, label: 'OmniFocus', class: 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400' },
  };

  $: cfg = config[source];
</script>

<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium {cfg.class}">
  <svelte:component this={cfg.icon} class="w-3 h-3" />
  {cfg.label}
</span>
```

### StatusIndicator

Status temps réel de Scapin dans le header :

```svelte
<script>
  export let status: 'active' | 'reasoning' | 'focus' | 'error' | 'paused';
  export let focusMinutes?: number;

  const config = {
    active: { color: 'bg-green-500', label: 'Actif', pulse: false },
    reasoning: { color: 'bg-blue-500', label: 'Raisonnement...', pulse: true },
    focus: { color: 'bg-amber-500', label: `Focus ${focusMinutes}min`, pulse: false },
    error: { color: 'bg-red-500', label: 'Erreur sync', pulse: false },
    paused: { color: 'bg-gray-400', label: 'En pause', pulse: false },
  };

  $: cfg = config[status];
</script>

<div class="flex items-center gap-2">
  <span class="relative flex h-3 w-3">
    {#if cfg.pulse}
      <span class="animate-ping absolute inline-flex h-full w-full rounded-full {cfg.color} opacity-75"></span>
    {/if}
    <span class="relative inline-flex rounded-full h-3 w-3 {cfg.color}"></span>
  </span>
  <span class="text-sm text-text-secondary">{cfg.label}</span>
</div>
```

---

## Configuration Tailwind

```javascript
// tailwind.config.js
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Sources
        'source-email': '#3b82f6',
        'source-teams': '#7c3aed',
        'source-calendar': '#10b981',
        'source-omnifocus': '#f97316',

        // Urgency
        'urgency-high': '#ef4444',
        'urgency-medium': '#f97316',
        'urgency-low': '#6b7280',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
};
```

---

## Responsive Breakpoints

```css
/* Mobile first (Tailwind defaults) */
sm: 640px    /* Phones landscape */
md: 768px    /* Tablets */
lg: 1024px   /* Laptops */
xl: 1280px   /* Desktops */
2xl: 1536px  /* Large screens */
```

| Breakpoint | Sidebar | Chat Panel | Layout |
|------------|---------|------------|--------|
| < md | Hidden (hamburger) | Hidden (FAB) | 1 column |
| md - lg | Collapsed (icons) | Overlay | 2 columns |
| lg - xl | Full | Collapsed | 2 columns |
| ≥ xl | Full | Full | 3 columns |

---

[< Architecture](./02-architecture.md) | [Suivant : Mockups Core >](./04-mockups-core.md)
