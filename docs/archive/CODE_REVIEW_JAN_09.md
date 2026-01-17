# Code Review — Scapin

**Dernière mise à jour** : 9 janvier 2026
**Origine** : Consolidation de BACKLOG_CODE_REVIEW.md (7 jan) et CODE_REVIEW_2026-01-08.md (8 jan)

---

## Synthèse Exécutive

| Catégorie | Total | Corrigé | Restant |
|-----------|-------|---------|---------|
| CRITICAL | 5 | 5 ✅ | 0 |
| HIGH | 11 | 11 ✅ | 0 |
| MEDIUM | 19 | 2 | 17 |
| LOW | 16 | 0 | 16 |

---

## CRITICAL — ✅ TOUS CORRIGÉS

1. ✅ **Deleted docs appearing in search** — Fixed in `vector_store.py`
2. ✅ **Timezone comparison crash** — Fixed in `note_metadata.py`
3. ✅ **Missing auth on notes endpoints** — Added `get_current_user` dependency
4. ✅ **Error messages exposing internals** — Sanitized exception handlers
5. ✅ **JWT Secret Key default** — Now required field, no default

---

## HIGH — ✅ TOUS CORRIGÉS (11/11)

| # | Issue | Status | Correction |
|---|-------|--------|------------|
| H1 | IMAP batch fetch (N+1 problem) | ✅ | `_fetch_emails_batch()` implemented |
| H2 | Rate limiting on login | ✅ | `rate_limiter.py` added |
| H3 | Index SQLite composite | ✅ | `idx_review_priority` added |
| H4 | Auth bypass warning | ✅ | Warning logged if auth disabled |
| H5 | Credentials rotation reminder | ✅ | Documented, .env in .gitignore |
| H6 | CORS trop permissif | ✅ | `config.api.cors_methods/headers` restreints |
| H7 | Origins CORS hardcodées | ✅ | Déplacé vers `config.api.cors_origins` |
| H8 | Exception details leakées | ✅ | Message générique retourné, full log séparé |
| H9 | WebSocket token en query param | ✅ | First message auth (query param deprecated) |
| H10 | Sync IMAP bloque event loop | ✅ | `asyncio.to_thread()` sur toutes ops IMAP |
| H11 | time.sleep() dans async | ✅ | Code sync exécuté via thread pool (to_thread) |

---

## MEDIUM — Backlog (17 items)

### Sécurité (3)
- **M1**: PIN faible (4-6 digits) — Requérir 8+ ou alphanumeric
- **M2**: Pas de token refresh JWT — Implémenter refresh tokens
- **M3**: No CSRF protection — Double-submit cookie pattern

### Architecture (5)
- **M4**: DI incohérent — Centraliser dans `deps.py`
- **M5**: Tight coupling CognitivePipeline — Injecter via interfaces
- **M6**: Global mutable singletons — FastAPI lifespan + scoped deps
- **M7**: Services créent leurs deps — Constructor injection
- **M8**: Mixing sync/async in deps — Use AsyncGenerator

### Performance (4)
- **M9**: JSON parsing par row — Lazy-load enrichment_history
- **M10**: Disk I/O par search result — Batch load notes
- **M11**: Embeddings en mémoire — Stocker dans FAISS seulement
- **M12**: time.sleep in recovery — async alternative

### Code Quality (5)
- **M13**: 273 `except Exception` dupliqués — Context manager utility
- **M14**: Fonctions >50 lignes — Extraire sous-fonctions
- **M15**: Magic numbers (20+) — `src/core/constants.py`
- **M16**: Data conversion duplication — Generic converter
- **M17**: Type safety gaps — TypedDict/dataclasses

---

## LOW — Nice-to-have (16 items)

### Architecture (5)
- Dead code `_build_dag()` — Implémenter ou supprimer
- Import `re` dupliqué — Move to module level
- Noms fonctions async dupliqués — Rename
- Interfaces non héritées — `class IMAPClient(IEmailClient)`
- Module boundaries unclear — Define `__all__`

### Code Quality (6)
- TODOs (20) — Create GitHub issues
- Logging f-strings (466) — Lazy formatting
- Missing docstrings — Add on public APIs
- Implicit state passing — Return explicitly
- Long functions (4) — Extract helpers

### Security (3)
- Some endpoints public when auth disabled — Review needs
- Logger may log PII — Sanitization
- No CSRF tokens — Add if needed

### Performance (2)
- No search caching — LRU with TTL
- Missing index errors table — If grows

---

## Points Positifs

1. **SQL Injection** : Parameterized queries partout ✅
2. **Path Traversal** : Protection robuste `note_manager.py` ✅
3. **Password Hashing** : bcrypt correctement utilisé ✅
4. **Input Validation** : Pydantic strict ✅
5. **Tests** : 2148+ tests, 95% coverage ✅
6. **Thread Safety** : CrossSourceCache avec RLock ✅
7. **Git Security** : `.env` dans `.gitignore` ✅

---

## Plan d'Action

### ✅ Court terme — COMPLÉTÉ
- [x] H6-H9: CORS + exceptions + WebSocket auth
- [x] H10-H11: Async IMAP + sleep fixes

### Moyen terme (prochain sprint)
- [ ] M13: Error handling utilities
- [ ] M15: Constants extraction
- [ ] M4: Centralized DI

### Long terme (backlog)
- [ ] Architecture patterns (M4-M8)
- [ ] Performance optimizations (M9-M12)
- [ ] Code quality improvements

---

*Document consolidé le 9 janvier 2026*
*Mis à jour le 9 janvier 2026 — Toutes issues CRITICAL et HIGH corrigées*
*Remplace : BACKLOG_CODE_REVIEW.md, CODE_REVIEW_2026-01-08.md*
