# Code Review — 8 janvier 2026

Analyse approfondie du codebase Scapin par 4 agents spécialisés :
- Sécurité
- Architecture
- Qualité de code
- Performance

---

## Synthèse Exécutive

| Catégorie | Critical | High | Medium | Low |
|-----------|----------|------|--------|-----|
| Sécurité | 3 | 4 | 4 | 3 |
| Architecture | 0 | 3 | 4 | 5 |
| Qualité Code | 0 | 2 | 6 | 4 |
| Performance | 0 | 2 | 5 | 4 |
| **Total** | **3** | **11** | **19** | **16** |

---

## CRITICAL — À corriger immédiatement

### 1. Credentials dans .env
- **Fichier** : `.env` (lignes 13-21, 40-42)
- **Description** : Le fichier `.env` contient des credentials réels :
  - iCloud email password : `xoiv-rxnh-xsqi-xisn`
  - Anthropic API key : `sk-ant-api03-I9ge...`
  - JWT secret key et PIN hash
- **Impact** : Si le repo est exposé, tous les credentials sont compromis
- **Action** :
  1. Rotation IMMÉDIATE de tous les credentials
  2. Vérifier que `.env` n'est pas dans l'historique git (`git log --all -- .env`)
  3. Si trouvé, purger avec `git filter-repo`
  4. Utiliser un gestionnaire de secrets (1Password CLI, keychain)

### 2. JWT Secret Key par défaut
- **Fichier** : `src/core/config_manager.py:627-628`
- **Description** : Default hardcodé : `"change-this-secret-key-in-production-min-32-chars"`
- **Impact** : Tokens forgeables si le default n'est pas changé
- **Action** :
  ```python
  jwt_secret_key: str = Field(
      ...,  # Required, no default
      min_length=32,
      description="Secret key for JWT signing"
  )
  ```

### 3. Authentication Bypass
- **Fichier** : `src/jeeves/api/deps.py:59-61`
- **Description** : Quand `config.auth.enabled=False`, auth complètement bypassée
- **Impact** : Tous les endpoints accessibles sans auth en dev
- **Action** :
  - Ajouter warning au startup si auth disabled
  - Considérer supprimer l'option de désactiver l'auth

---

## HIGH — À traiter rapidement

### 4. CORS trop permissif
- **Fichier** : `src/jeeves/api/app.py:66-72`
- **Description** : `allow_methods=["*"]` et `allow_headers=["*"]`
- **Impact** : Facilite potentiellement les attaques CSRF
- **Action** :
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=config.api.cors_origins,
      allow_credentials=True,
      allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
      allow_headers=["Authorization", "Content-Type"],
  )
  ```

### 5. Origins CORS hardcodées
- **Fichier** : `src/jeeves/api/app.py:68`
- **Description** : `["http://localhost:3000", "http://localhost:5173"]` hardcodé
- **Action** : Déplacer vers configuration `config.api.cors_origins`

### 6. Exception details leakées
- **Fichier** : `src/jeeves/api/app.py:75-89`
- **Description** : `str(exc)` retourné au client, peut contenir des infos sensibles
- **Action** :
  ```python
  return JSONResponse(
      status_code=500,
      content=APIResponse(
          success=False,
          error="Internal server error",  # Generic
      ).model_dump(mode="json"),
  )
  ```

### 7. WebSocket token en query parameter
- **Fichier** : `src/jeeves/api/websocket/router.py:23`
- **Description** : JWT passé via `?token=XXX`
- **Impact** : Token visible dans logs serveur, historique browser, URLs partagées
- **Action** : Passer le token dans le premier message WebSocket après connexion

### 8. Sync IMAP bloque l'event loop
- **Fichier** : `src/jeeves/api/services/email_service.py:105,161-196`
- **Description** : Méthodes async appellent des opérations IMAP synchrones
- **Impact** : Bloque tout le serveur FastAPI pendant les opérations IMAP
- **Action** :
  ```python
  async def process_inbox(...):
      results = await asyncio.to_thread(processor.process_inbox, **kwargs)
  ```

### 9. Fetch email un par un (N+1)
- **Fichier** : `src/integrations/email/imap_client.py:418-428`
- **Description** : Chaque email fetché individuellement dans une boucle
- **Impact** : Lent sur connexions à haute latence
- **Action** : Utiliser batch fetch IMAP :
  ```python
  self._connection.fetch(b':'.join(id_list), '(BODY.PEEK[])')
  ```

### 10. time.sleep() bloque dans code async
- **Fichier** : `src/sancho/router.py:188,390,430,445,457,478`
- **Description** : `time.sleep()` dans retry loops bloque le thread entier
- **Impact** : Peut bloquer jusqu'à 30s pendant retries
- **Action** :
  - Contexte async : `await asyncio.sleep()`
  - Contexte sync : `threading.Event().wait(timeout)`

### 11. DI incohérent
- **Fichier** : `src/jeeves/api/deps.py`
- **Description** : Seulement 3 services dans deps.py, autres créés directement dans routers
- **Impact** : Difficile à tester, patterns incohérents
- **Action** : Centraliser toutes les factory functions dans `deps.py`

---

## MEDIUM — Planifier pour prochain sprint

### 12. 273 `except Exception` dupliqués
- **Fichiers** : Global (imap_client.py: 17, figaro/actions: 8, cognitive_pipeline.py: 6...)
- **Description** : Pattern identique répété 273 fois
- **Action** : Créer utilitaires dans `src/core/error_handling.py` :
  ```python
  @contextmanager
  def handle_errors(operation: str, logger, default=None):
      try:
          yield
      except Exception as e:
          logger.error(f"Failed to {operation}: {e}", exc_info=True)
          return default
  ```

### 13. Pas de rate limiting sur login
- **Fichier** : `src/jeeves/api/routers/auth.py`
- **Description** : Endpoint `/api/auth/login` sans rate limiting
- **Impact** : Vulnérable aux attaques brute-force (PIN 4-6 digits = max 1M combinaisons)
- **Action** : Ajouter `slowapi` + exponential backoff + lockout après N échecs

### 14. Pas de token refresh
- **Fichier** : `src/jeeves/api/auth/jwt_handler.py`
- **Description** : JWT 7 jours sans mécanisme de refresh
- **Impact** : Long-lived tokens à risque si volés
- **Action** : Implémenter refresh tokens avec access token courte durée

### 15. PIN faible
- **Fichier** : `src/jeeves/api/auth/password.py`
- **Description** : 4-6 digits = max 1M combinaisons
- **Impact** : Vulnérable au brute-force sans rate limiting
- **Action** : Requérir PIN 8+ digits ou passwords alphanumériques

### 16. Tight coupling CognitivePipeline
- **Fichier** : `src/trivelin/cognitive_pipeline.py:20-29`
- **Description** : Imports directs de 5 modules différents
- **Impact** : High fan-out coupling, difficile à tester
- **Action** : Injecter dépendances via interfaces/protocols

### 17. Global mutable singletons
- **Fichiers** : `state_manager.py:357-387`, `deps.py:24-39`
- **Description** : Singletons mutables avec état persistant entre requêtes
- **Impact** : State leaks, difficile à tester, thread safety issues
- **Action** : Utiliser FastAPI lifespan + scoped dependencies

### 18. Services créent leurs dépendances
- **Fichier** : `src/jeeves/api/services/queue_service.py:146-158`
- **Description** : Lazy import + instantiation d'infra dans les méthodes
- **Impact** : Viole SRP, difficile à tester
- **Action** : Injecter clients pré-configurés via constructor

### 19. JSON parsing répété
- **Fichier** : `src/passepartout/note_metadata.py:236-241`
- **Description** : `json.loads()` sur `enrichment_history` pour chaque row
- **Impact** : Lent pour bulk operations (list_all, get_due_for_review)
- **Action** : Lazy-load enrichment_history ou table séparée

### 20. Index SQLite manquant
- **Fichier** : `src/passepartout/note_metadata.py:199-211`
- **Description** : Index individuels mais pas de composite
- **Impact** : Queries sur (importance, next_review, note_type) non optimisées
- **Action** :
  ```sql
  CREATE INDEX IF NOT EXISTS idx_review_priority
  ON note_metadata(importance, next_review, note_type)
  ```

### 21. Magic numbers
- **Fichiers** : Global (processor.py, router.py, generator.py...)
- **Description** : 20+ valeurs hardcodées (10000, 60, 30, 200, 0.8...)
- **Action** : Extraire vers `src/core/constants.py`

### 22. Disk I/O par résultat search
- **Fichier** : `src/passepartout/note_manager.py:394-400`
- **Description** : `get_note()` appelé pour chaque résultat de recherche
- **Impact** : Lent pour grands résultats
- **Action** : Batch load notes en une passe

### 23. Embeddings stockés en mémoire
- **Fichier** : `src/passepartout/vector_store.py:144-149`
- **Description** : Full embeddings gardés dans `id_to_doc`
- **Impact** : ~15MB pour 10K docs (croissance linéaire)
- **Action** : Ne garder que doc_id + metadata, embeddings dans FAISS seulement

---

## LOW — Nice to have

### 24. Méthode `_build_dag` non utilisée
- **Fichier** : `src/figaro/orchestrator.py:272-287`
- **Description** : Code mort, DAG jamais exécuté
- **Action** : Implémenter parallel execution ou supprimer

### 25. Import `re` dupliqué
- **Fichier** : `src/integrations/email/imap_client.py:51,105`
- **Description** : `import re` apparaît 2 fois dans des fonctions
- **Action** : Déplacer au niveau module

### 26. Noms de fonctions async dupliqués
- **Fichier** : `src/jeeves/cli.py:442,636`
- **Description** : `poll_loop()` et `single_run()` définis 2 fois (nested)
- **Action** : Renommer : `_teams_poll_loop()`, `_calendar_poll_loop()`

### 27. Fonctions complexes (>50 lignes)
- **Fichiers** :
  - `router.py:284` — `analyze_email()` 204 lignes
  - `processor.py:217` — `process_inbox()` 156 lignes
  - `imap_client.py:593` — `_extract_content()` 137 lignes
- **Action** : Extraire en sous-fonctions plus petites

### 28. 20 TODO comments
- **Fichiers** : processor.py, notes_service.py, search_service.py, knowledge_updater.py
- **TODOs critiques** :
  - `processor.py:716` — Intégrer OmniFocus MCP
  - `notes_service.py:711,726` — Apple Notes sync integration
  - `search_service.py:377,398` — Calendar/Teams search
- **Action** : Créer issues GitHub pour tracking

### 29. Interfaces non implémentées explicitement
- **Fichier** : `src/core/interfaces.py`
- **Description** : `IEmailClient` défini mais `IMAPClient` n'hérite pas explicitement
- **Action** : `class IMAPClient(IEmailClient):`

### 30. Type safety gaps
- **Fichier** : `src/core/state_manager.py:158-171`
- **Description** : `get()` et `set()` utilisent `Any`
- **Action** : TypedDict ou dataclasses pour shapes connues

### 31. Logging avec f-strings (466 occurrences)
- **Fichiers** : Global
- **Description** : `logger.error(f"...")` au lieu de `logger.error("...", var)`
- **Impact** : f-strings évalués même si log level disabled
- **Action** : Utiliser lazy formatting : `logger.error("Failed: %s", e)`

---

## Points Positifs

1. **SQL Injection** : Toutes les requêtes SQLite utilisent paramètres (`?`)
2. **Path Traversal** : Protection robuste dans `note_manager.py` (resolve + validation)
3. **Password Hashing** : bcrypt correctement utilisé
4. **Input Validation** : Pydantic enforces strict validation
5. **Tests** : 1824 tests, 95% couverture
6. **Thread Safety Cache** : CrossSourceCache protégé par RLock (ajouté session précédente)
7. **Git Ignore** : `.env` correctement dans `.gitignore`
8. **Secrets Module** : Intégration keychain disponible

---

## Plan d'Action Recommandé

### Immédiat (cette semaine)
- [ ] #1 Rotation credentials .env
- [ ] #2 JWT secret obligatoire
- [ ] #3 Warning auth disabled

### Court terme (2 semaines)
- [ ] #4-7 CORS + exceptions + WebSocket auth
- [ ] #8-10 Async IMAP + batch fetch + sleep fix
- [ ] #13 Rate limiting login

### Moyen terme (sprint suivant)
- [ ] #12 Error handling utilities
- [ ] #20 Index SQLite composite
- [ ] #21 Constants extraction
- [ ] #11 DI centralisé

### Long terme (backlog)
- [ ] #16-18 Architecture patterns
- [ ] #22-23 Performance optimizations
- [ ] #24-31 Code quality improvements

---

## Références

- **Security Audit** : Agent ac5f865
- **Architecture Review** : Agent a253216
- **Code Quality Review** : Agent ac6cccd
- **Performance Review** : Agent aabf978

---

*Document généré le 8 janvier 2026*
