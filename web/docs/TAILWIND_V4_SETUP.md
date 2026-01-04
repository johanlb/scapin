# Configuration Tailwind CSS v4 avec SvelteKit

## Contexte

Tailwind CSS v4 introduit une nouvelle architecture basée sur CSS natif. Avec le plugin `@tailwindcss/vite`, la configuration est différente de v3.

## Problème rencontré

Les classes utilitaires Tailwind (`fixed`, `hidden`, `md:flex`, etc.) n'étaient pas générées car :
1. `@tailwindcss/vite` ne lit pas automatiquement `tailwind.config.ts`
2. Les directives `@source` dans le CSS ne fonctionnaient pas avec le plugin Vite

## Solution

### 1. Créer `tailwind.config.ts` à la racine du projet

```typescript
import type { Config } from 'tailwindcss';

export default {
  content: [
    './src/**/*.{html,js,svelte,ts}',
    './src/routes/**/*.{svelte,ts}',
    './src/lib/**/*.{svelte,ts}'
  ]
} satisfies Config;
```

### 2. Importer la config dans `src/app.css`

```css
@import "tailwindcss";
@config "../tailwind.config.ts";

/* Vos styles personnalisés... */
```

### 3. Configuration Vite (`vite.config.ts`)

```typescript
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()]
});
```

**Important** : `tailwindcss()` doit être AVANT `sveltekit()` dans l'array des plugins.

## Versions testées

- tailwindcss: ^4.1.18
- @tailwindcss/vite: ^4.1.18
- @sveltejs/kit: ^2.49.1
- svelte: ^5.45.6
- vite: ^7.2.6

## Outils de debug

### Screenshots automatiques avec Playwright

```bash
# Installer
npm install -D playwright @playwright/test
npx playwright install chromium

# Utiliser
node screenshot.mjs
```

Le script `screenshot.mjs` génère :
- `/tmp/scapin-desktop.png` (1280x800)
- `/tmp/scapin-mobile.png` (390x844)

## Références

- [Tailwind CSS v4 Documentation](https://tailwindcss.com/docs/v4-beta)
- [SvelteKit + Tailwind](https://tailwindcss.com/docs/guides/sveltekit)
