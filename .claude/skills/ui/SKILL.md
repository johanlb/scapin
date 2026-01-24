---
name: ui
description: Best practices UI/Frontend - Patterns Svelte 5, design tokens, accessibilité, performance. Utiliser pour créer ou améliorer des composants UI.
allowed-tools: Read, Grep, Glob, WebSearch
---

# Best Practices UI (2025)

Guide des meilleures pratiques frontend pour Scapin.

> Sources : [Render Blog](https://render.com/blog/svelte-design-patterns), [W3C APG](https://www.w3.org/WAI/ARIA/apg/), [web.dev](https://web.dev/articles/optimize-lcp), [Penpot](https://penpot.app/blog/the-developers-guide-to-design-tokens-and-css-variables)

---

## Svelte 5 Patterns

### 1. Compound Components

Quand un composant dépasse **3-4 props** pour layout/contenu, le refactorer en compound components.

```svelte
<!-- ❌ Trop de props -->
<Card
  title="Mon titre"
  subtitle="Sous-titre"
  icon="📝"
  actions={[{label: "Edit"}, {label: "Delete"}]}
  footer="Footer text"
/>

<!-- ✅ Compound components -->
<Card>
  <Card.Header icon="📝">
    <Card.Title>Mon titre</Card.Title>
    <Card.Subtitle>Sous-titre</Card.Subtitle>
  </Card.Header>
  <Card.Content>...</Card.Content>
  <Card.Actions>
    <Button>Edit</Button>
    <Button>Delete</Button>
  </Card.Actions>
</Card>
```

**Export pattern (shadcn-svelte style) :**

```typescript
// components/card/index.ts
export { default as Card } from './Card.svelte';
export { default as CardHeader } from './CardHeader.svelte';
export { default as CardTitle } from './CardTitle.svelte';
export { default as CardContent } from './CardContent.svelte';
export { default as CardActions } from './CardActions.svelte';
```

### 2. Snippets (remplacent les slots)

```svelte
<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    header: Snippet;
    children: Snippet;
    footer?: Snippet<[{ count: number }]>;  // Snippet avec paramètres
  }

  let { header, children, footer }: Props = $props();
  let count = $state(0);
</script>

<div class="card">
  <header>{@render header()}</header>
  <main>{@render children()}</main>
  {#if footer}
    <footer>{@render footer({ count })}</footer>
  {/if}
</div>

<!-- Usage -->
<Card>
  {#snippet header()}
    <h2>Titre</h2>
  {/snippet}

  <p>Contenu principal</p>

  {#snippet footer({ count })}
    <span>{count} items</span>
  {/snippet}
</Card>
```

### 3. Context API (état partagé parent-enfant)

```svelte
<!-- Parent.svelte -->
<script>
  import { setContext } from 'svelte';

  const state = $state({ expanded: false });
  setContext('accordion', {
    get expanded() { return state.expanded; },
    toggle: () => state.expanded = !state.expanded
  });
</script>

<!-- Child.svelte -->
<script>
  import { getContext } from 'svelte';

  const { expanded, toggle } = getContext('accordion');
</script>

<button onclick={toggle}>
  {expanded ? 'Collapse' : 'Expand'}
</button>
```

### 4. Règles $derived vs $effect

| Rune | Usage | Caractéristique |
|------|-------|-----------------|
| `$derived` | Calculs, transformations | **Pur**, retourne une valeur |
| `$effect` | API calls, localStorage, logs | **Impur**, side effects |

```svelte
<script>
  let items = $state([]);

  // ✅ $derived pour calculs
  const total = $derived(items.reduce((sum, i) => sum + i.price, 0));
  const isEmpty = $derived(items.length === 0);

  // ✅ $effect pour side effects
  $effect(() => {
    localStorage.setItem('cart', JSON.stringify(items));
  });

  // ❌ NE PAS utiliser $effect pour des calculs
  // let total = 0;
  // $effect(() => { total = items.reduce(...) }); // MAUVAIS
</script>
```

---

## Design Tokens & CSS

### Structure des Tokens (3 niveaux)

```css
:root {
  /* 1. Primitives (valeurs brutes) */
  --color-blue-500: #3b82f6;
  --color-blue-600: #2563eb;
  --spacing-4: 1rem;
  --radius-md: 0.5rem;

  /* 2. Semantic (intention) */
  --color-primary: var(--color-blue-600);
  --color-interactive: var(--color-blue-500);
  --color-text-primary: #1a1a1a;
  --color-text-secondary: #6b7280;

  /* 3. Component (spécifique) */
  --button-bg: var(--color-primary);
  --button-radius: var(--radius-md);
  --card-padding: var(--spacing-4);
}

/* Dark mode */
[data-theme="dark"] {
  --color-text-primary: #f5f5f5;
  --color-text-secondary: #a1a1aa;
}
```

### Convention de Nommage

Format : `--{category}-{property}-{variant}`

```css
/* Exemples */
--color-bg-primary
--color-bg-secondary
--color-text-muted
--spacing-sm
--spacing-md
--radius-lg
--shadow-md
```

### Glass Morphism (Design Scapin)

```css
.glass {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
}

.glass-subtle {
  background: var(--glass-subtle);
}

.glass-prominent {
  background: var(--glass-prominent);
  box-shadow: var(--shadow-lg);
}
```

---

## Accessibilité (a11y)

### Checklist Obligatoire

```
□ Semantic HTML (<button>, <nav>, <main>, pas divs)
□ Keyboard navigation (Tab, Enter, Escape, Arrow keys)
□ Focus visible sur tous les éléments interactifs
□ Contraste texte ≥ 4.5:1 (AA) ou 7:1 (AAA)
□ Labels sur tous les inputs (<label for="...">)
□ Alt text sur les images informatives
□ ARIA uniquement si HTML sémantique insuffisant
```

### Patterns ARIA Courants

```svelte
<!-- Button avec état -->
<button
  aria-pressed={isActive}
  aria-expanded={isOpen}
  aria-label="Fermer le menu"
>

<!-- Live regions (annonces screen reader) -->
<div aria-live="polite" aria-atomic="true">
  {statusMessage}
</div>

<!-- Dialog/Modal -->
<div
  role="dialog"
  aria-modal="true"
  aria-labelledby="dialog-title"
>
  <h2 id="dialog-title">Confirmer</h2>
</div>

<!-- Navigation -->
<nav aria-label="Navigation principale">
  <ul role="list">...</ul>
</nav>
```

### Keyboard Patterns

| Composant | Keys |
|-----------|------|
| Button | Enter, Space |
| Menu | Arrow keys, Enter, Escape |
| Modal | Escape pour fermer, Tab trap |
| Tabs | Arrow keys pour naviguer |
| Combobox | Arrow keys, Enter, Escape |

```svelte
<script>
  function handleKeydown(event: KeyboardEvent) {
    switch (event.key) {
      case 'Escape':
        close();
        break;
      case 'ArrowDown':
        event.preventDefault();
        focusNext();
        break;
      case 'ArrowUp':
        event.preventDefault();
        focusPrevious();
        break;
    }
  }
</script>

<div onkeydown={handleKeydown} tabindex="0">
```

### Contraste Minimum

| Élément | Ratio AA | Ratio AAA |
|---------|----------|-----------|
| Texte normal | 4.5:1 | 7:1 |
| Texte large (18px+) | 3:1 | 4.5:1 |
| Éléments UI | 3:1 | 3:1 |

---

## Performance (Core Web Vitals)

### Métriques Cibles

| Métrique | Cible | Mesure |
|----------|-------|--------|
| **LCP** | < 2.5s | Largest Contentful Paint |
| **INP** | < 200ms | Interaction to Next Paint |
| **CLS** | < 0.1 | Cumulative Layout Shift |

### Optimisations LCP

```svelte
<!-- 1. Priorité fetch pour image LCP -->
<img
  src={heroImage}
  alt="Hero"
  fetchpriority="high"
  loading="eager"
/>

<!-- 2. Preload des ressources critiques -->
<svelte:head>
  <link rel="preload" href="/fonts/inter.woff2" as="font" crossorigin />
  <link rel="preload" href={heroImage} as="image" />
</svelte:head>

<!-- 3. Inline critical CSS -->
<style>
  /* CSS critique pour above-the-fold inline ici */
</style>
```

### Optimisations CLS

```svelte
<!-- 1. TOUJOURS définir width/height sur images -->
<img src={src} alt={alt} width="800" height="600" />

<!-- 2. Réserver l'espace pour contenu dynamique -->
<div class="skeleton" style="min-height: 200px;">
  {#if loaded}
    <DynamicContent />
  {:else}
    <LoadingPlaceholder />
  {/if}
</div>

<!-- 3. Éviter les insertions DOM au-dessus du viewport -->
```

### Optimisations INP

```svelte
<script>
  // 1. Debounce les handlers fréquents
  import { debounce } from '$lib/utils';

  const handleInput = debounce((value: string) => {
    // Traitement lourd
  }, 150);

  // 2. Différer le travail non-critique
  async function handleClick() {
    // Feedback immédiat
    showSpinner = true;

    // Travail lourd après paint
    await tick();
    await heavyComputation();

    showSpinner = false;
  }
</script>

<!-- 3. Éviter les layouts synchrones forcés -->
```

### Lazy Loading

```svelte
<!-- Images below fold -->
<img src={src} alt={alt} loading="lazy" />

<!-- Composants lourds -->
{#await import('./HeavyComponent.svelte') then { default: Component }}
  <Component />
{/await}

<!-- Intersection Observer pour infinite scroll -->
<script>
  import { onMount } from 'svelte';

  let sentinel: HTMLElement;

  onMount(() => {
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) {
        loadMore();
      }
    });
    observer.observe(sentinel);
    return () => observer.disconnect();
  });
</script>

<div bind:this={sentinel} class="sentinel" />
```

---

## Checklist Composant UI

Avant de livrer un composant :

```
□ Props typées avec interface Props
□ Valeurs par défaut sensées
□ Keyboard accessible
□ Focus states visibles
□ ARIA labels si nécessaire
□ Responsive (mobile-first)
□ Dark mode supporté (CSS variables)
□ Loading/Error states gérés
□ Pas de layout shift (dimensions fixes ou skeleton)
□ Images optimisées (WebP, lazy loading)
```

---

## Anti-patterns UI

| ❌ Ne pas faire | ✅ Faire |
|-----------------|----------|
| Div avec onclick | `<button>` sémantique |
| Props > 5 pour layout | Compound components |
| `$effect` pour calculs | `$derived` |
| Couleurs hardcodées | CSS variables |
| Images sans dimensions | width/height explicites |
| Focus invisible | `:focus-visible` styles |
| Texte sur image sans contraste | Overlay ou text-shadow |

---

## Ressources

- [W3C ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [A11Y Project Checklist](https://www.a11yproject.com/checklist/)
- [web.dev Performance](https://web.dev/articles/optimize-lcp)
- [Svelte 5 Documentation](https://svelte.dev/docs)
- [shadcn-svelte](https://www.shadcn-svelte.com/) (patterns de composants)
