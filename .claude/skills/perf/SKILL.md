---
name: perf
description: Performance Scapin - Métriques, profiling, optimisations backend et frontend. Utiliser pour diagnostiquer ou améliorer les performances.
allowed-tools: Bash, Read, Grep, Glob
---

# Performance Scapin

Guide pour mesurer, diagnostiquer et optimiser les performances.

---

## Métriques Clés

### Backend

| Métrique | Cible | Alerte |
|----------|-------|--------|
| **API Response Time** (p95) | < 200ms | > 500ms |
| **Queue Processing** | < 5s/email | > 15s |
| **Multi-Pass Convergence** | 2-3 passes | > 4 passes |
| **Memory Usage** | < 512MB | > 1GB |
| **FAISS Search** | < 50ms | > 200ms |

### Frontend

| Métrique | Cible | Alerte |
|----------|-------|--------|
| **LCP** | < 2.5s | > 4s |
| **INP** | < 200ms | > 500ms |
| **CLS** | < 0.1 | > 0.25 |
| **Bundle Size** | < 500KB | > 1MB |
| **Hydration** | < 500ms | > 1s |

---

## Commandes de Diagnostic

### Profiling Backend

```bash
# Profiler une commande avec cProfile
python -m cProfile -s cumulative scapin.py process --limit 5

# Profiler avec py-spy (temps réel, sans modification)
py-spy top -- python scapin.py serve

# Générer un flamegraph
py-spy record -o flamegraph.svg -- python scapin.py process --limit 10

# Memory profiling
python -m memory_profiler scapin.py process --limit 5

# Tracemalloc pour fuites mémoire
python -c "
import tracemalloc
tracemalloc.start()
# ... run code ...
snapshot = tracemalloc.take_snapshot()
for stat in snapshot.statistics('lineno')[:10]:
    print(stat)
"
```

### Profiling Frontend

```bash
# Build avec analyse de bundle
cd web && npm run build -- --analyze

# Lighthouse CI
npx lighthouse http://localhost:5173 --output html --output-path ./report.html

# Mesurer Core Web Vitals
npx web-vitals-cli http://localhost:5173
```

### Benchmarks Base de Données

```bash
# Temps de requête SQLite
sqlite3 data/scapin.db ".timer on" "SELECT COUNT(*) FROM notes;"

# Explain query plan
sqlite3 data/scapin.db "EXPLAIN QUERY PLAN SELECT * FROM notes WHERE title LIKE '%test%';"

# Stats FAISS
python -c "
import faiss
idx = faiss.read_index('data/faiss/notes.index')
print(f'Vectors: {idx.ntotal}')
print(f'Dimension: {idx.d}')
"
```

---

## Optimisations Backend

### 1. Async I/O

```python
# ❌ Bloquant
def get_data():
    return requests.get(url).json()

# ✅ Non-bloquant
async def get_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# ✅ Pour code sync legacy
import asyncio
result = await asyncio.to_thread(sync_function, arg1, arg2)
```

### 2. Batch Processing

```python
# ❌ N requêtes
for item in items:
    await process(item)

# ✅ Batch avec TaskGroup
async with asyncio.TaskGroup() as tg:
    tasks = [tg.create_task(process(item)) for item in items]

# ✅ Avec semaphore pour limiter concurrence
semaphore = asyncio.Semaphore(10)

async def limited_process(item):
    async with semaphore:
        return await process(item)

async with asyncio.TaskGroup() as tg:
    tasks = [tg.create_task(limited_process(item)) for item in items]
```

### 3. Caching

```python
from functools import lru_cache
from cachetools import TTLCache

# Cache en mémoire (données statiques)
@lru_cache(maxsize=1000)
def get_config(key: str) -> str:
    return load_config()[key]

# Cache avec TTL (données qui expirent)
cache = TTLCache(maxsize=100, ttl=300)  # 5 minutes

async def get_note(note_id: str) -> Note:
    if note_id in cache:
        return cache[note_id]
    note = await db.get_note(note_id)
    cache[note_id] = note
    return note
```

### 4. Lazy Loading

```python
# ❌ Charge tout au démarrage
class Service:
    def __init__(self):
        self.heavy_resource = load_heavy_resource()

# ✅ Charge à la demande
class Service:
    _heavy_resource: Resource | None = None

    @property
    def heavy_resource(self) -> Resource:
        if self._heavy_resource is None:
            self._heavy_resource = load_heavy_resource()
        return self._heavy_resource
```

### 5. Database Optimization

```python
# ❌ N+1 queries
notes = await db.get_all_notes()
for note in notes:
    note.tags = await db.get_tags(note.id)  # N queries!

# ✅ JOIN ou batch
notes = await db.get_notes_with_tags()  # 1 query with JOIN

# ✅ Index sur colonnes filtrées
# CREATE INDEX idx_notes_folder ON notes(folder_path);
# CREATE INDEX idx_notes_updated ON notes(updated_at DESC);
```

---

## Optimisations Frontend

### 1. Bundle Splitting

```typescript
// ❌ Import statique de composant lourd
import HeavyChart from './HeavyChart.svelte';

// ✅ Import dynamique
{#await import('./HeavyChart.svelte') then { default: HeavyChart }}
    <HeavyChart {data} />
{/await}
```

### 2. Virtual Lists

```svelte
<script>
    // Pour listes > 100 items, utiliser virtualisation
    import { VirtualList } from 'svelte-virtual-list';
</script>

<VirtualList items={largeList} let:item>
    <ListItem {item} />
</VirtualList>
```

### 3. Memoization avec $derived

```svelte
<script>
    let items = $state<Item[]>([]);
    let filter = $state('');

    // ✅ $derived ne recalcule que si items ou filter changent
    const filteredItems = $derived(
        items.filter(i => i.name.includes(filter))
    );

    // ✅ Calcul coûteux mémorisé
    const expensiveResult = $derived.by(() => {
        return items.reduce((acc, item) => {
            // calcul complexe...
            return acc;
        }, initialValue);
    });
</script>
```

### 4. Debounce & Throttle

```svelte
<script>
    import { debounce } from '$lib/utils';

    let searchQuery = $state('');

    // ✅ Debounce pour éviter trop de requêtes
    const debouncedSearch = debounce((query: string) => {
        fetchResults(query);
    }, 300);

    $effect(() => {
        if (searchQuery.length >= 2) {
            debouncedSearch(searchQuery);
        }
    });
</script>
```

### 5. Image Optimization

```svelte
<!-- ✅ Lazy loading pour images below fold -->
<img src={src} alt={alt} loading="lazy" decoding="async" />

<!-- ✅ Dimensions explicites (évite CLS) -->
<img src={src} alt={alt} width="800" height="600" />

<!-- ✅ Srcset pour responsive -->
<img
    src={src}
    srcset="{src_small} 400w, {src_medium} 800w, {src_large} 1200w"
    sizes="(max-width: 600px) 400px, (max-width: 1200px) 800px, 1200px"
    alt={alt}
/>
```

---

## Monitoring en Production

### Métriques à Surveiller

```python
# src/monitoring/metrics.py
from dataclasses import dataclass
from time import perf_counter
from contextlib import contextmanager

@dataclass
class PerformanceMetrics:
    api_response_times: list[float]
    queue_processing_times: list[float]
    multi_pass_counts: list[int]

    def p95_response_time(self) -> float:
        sorted_times = sorted(self.api_response_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[idx] if sorted_times else 0

@contextmanager
def measure_time(metric_name: str):
    start = perf_counter()
    yield
    duration = perf_counter() - start
    logger.info(f"Performance: {metric_name}", extra={
        "metric": metric_name,
        "duration_ms": duration * 1000
    })
```

### Health Check avec Métriques

```python
@router.get("/api/health")
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        checks={
            "database": await check_db_connection(),
            "faiss": await check_faiss_index(),
            "api_latency_p95": metrics.p95_response_time(),
            "queue_size": await get_queue_size(),
            "memory_mb": get_memory_usage_mb(),
        }
    )
```

---

## Checklist Performance

### Avant Merge

```
□ Pas de N+1 queries (vérifier avec logging SQL)
□ Pas de calculs synchrones bloquants dans async
□ Images avec dimensions explicites
□ Composants lourds en lazy loading
□ Pas de re-renders inutiles (vérifier avec Svelte DevTools)
□ Bundle size vérifié (npm run build -- --analyze)
```

### Après Déploiement

```
□ Lighthouse score > 90
□ API p95 < 200ms
□ Pas de memory leak (surveiller sur 24h)
□ Queue ne s'accumule pas
```

---

## Outils Recommandés

| Outil | Usage |
|-------|-------|
| **py-spy** | Profiling Python sans overhead |
| **memory_profiler** | Tracking mémoire ligne par ligne |
| **Lighthouse** | Audit performance frontend |
| **Svelte DevTools** | Debug re-renders |
| **sqlite3 .timer** | Benchmark queries |

---

## Anti-patterns Performance

| ❌ Ne pas faire | ✅ Faire |
|-----------------|----------|
| `await` dans une boucle | `asyncio.TaskGroup` |
| SELECT * sans LIMIT | Pagination |
| Re-render composant entier | $derived granulaire |
| Import statique gros composant | import() dynamique |
| Calculer dans template | $derived |
| Polling API sans throttle | WebSocket ou long-polling |
| Charger toute la liste | Virtual list |

---

## Ressources

- [py-spy](https://github.com/benfred/py-spy) — Profiler Python
- [web.dev Performance](https://web.dev/performance/)
- [Svelte Performance Tips](https://svelte.dev/docs/svelte/v5-migration-guide#Performance)
