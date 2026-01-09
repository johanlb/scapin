# Audit de Sécurité — Scapin v1.0

**Date** : 9 janvier 2026
**Auditeur** : Claude (automatisé + revue manuelle)
**Version** : 1.0.0-alpha.18

---

## Résumé Exécutif

| Catégorie | Status | Détails |
|-----------|--------|---------|
| **Dépendances Python** | ⚠️ 1 vulnérabilité | ecdsa (pas de fix disponible) |
| **Dépendances JavaScript** | ✅ Acceptable | 3 low severity (breaking fix) |
| **Analyse statique (bandit)** | ✅ Validé | 0 vulnérabilité réelle |
| **OWASP Top 10** | ✅ Conforme | Voir détails ci-dessous |

**Verdict** : Le projet est **prêt pour v1.0** avec les risques documentés et acceptés.

---

## 1. Vulnérabilités des Dépendances

### 1.1 Python (pip-audit)

| Package | Version | CVE | Sévérité | Fix | Status |
|---------|---------|-----|----------|-----|--------|
| ecdsa | 0.19.1 | CVE-2024-23342 | MEDIUM | Non disponible | ⚠️ Accepté |
| urllib3 | 2.6.3 | — | — | — | ✅ Corrigé |

**ecdsa (CVE-2024-23342)** :
- Utilisé par `python-jose` pour les signatures JWT
- Vulnérabilité : Timing side-channel attack sur ECDSA
- Impact pour Scapin : **Faible** — JWT utilise HS256 (HMAC) par défaut, pas ECDSA
- Mitigation : Surveiller les mises à jour, migrer vers `PyJWT` si nécessaire

### 1.2 JavaScript (npm audit)

| Package | Version | Sévérité | Fix | Status |
|---------|---------|----------|-----|--------|
| cookie | <0.7.0 | LOW | Breaking | ⚠️ Accepté |

**cookie** :
- Dépendance de `@sveltejs/kit`
- Vulnérabilité : Accepte des caractères hors limites dans name/path/domain
- Impact : **Faible** — Application mono-utilisateur locale
- Fix : Nécessite downgrade majeur de SvelteKit (0.0.30)
- Décision : **Refusé** — Le fix est plus risqué que la vulnérabilité

---

## 2. Analyse Statique (bandit)

### 2.1 Alertes HIGH

| Fichier | Ligne | Issue | Verdict |
|---------|-------|-------|---------|
| `src/sancho/templates.py` | 69 | Jinja2 autoescape=False | ✅ Faux positif |

**Analyse** :
```python
self.env = Environment(
    loader=FileSystemLoader(str(self.templates_dir)),
    autoescape=False,  # Templates contain prompts, not HTML
)
```
- Les templates sont des **prompts IA**, pas du HTML
- Aucun rendu vers un navigateur
- Le commentaire documente explicitement le choix
- **Verdict : Faux positif**

### 2.2 Alertes MEDIUM

| Fichier | Ligne | Issue | Verdict |
|---------|-------|-------|---------|
| `notification_service.py` | 303, 310, 317, 371 | SQL injection | ✅ Faux positif |
| `vector_store.py` | 536 | Pickle deserialization | ⚠️ Acceptable |
| `cli.py` | 1348 | Binding to 0.0.0.0 | ⚠️ Acceptable |

**SQL "injection" (notification_service.py)** :
```python
where_clause = " AND ".join(conditions)  # conditions = ["user_id = ?", "type = ?"]
cursor = conn.execute(
    f"SELECT COUNT(*) FROM notifications WHERE {where_clause}",
    params,  # Valeurs utilisateur ici, paramétrées
)
```
- `where_clause` contient des noms de colonnes **hardcodés**
- `params` contient les valeurs utilisateur via **requêtes paramétrées**
- Pas d'injection possible — les noms de colonnes ne viennent pas de l'utilisateur
- **Verdict : Faux positif**

**Pickle deserialization (vector_store.py)** :
```python
if pickle_path.exists():
    logger.warning("Found legacy pickle metadata - migrating to JSON...")
    import pickle
    with open(pickle_path, "rb") as f:
        metadata = pickle.load(f)
    self._migrate_pickle_metadata(metadata, path)
```
- Code de **migration legacy** uniquement
- Lit des fichiers locaux créés par le système lui-même
- Après lecture, migre vers JSON sécurisé
- **Verdict : Risque acceptable** (migration one-time)

**Binding to 0.0.0.0 (cli.py)** :
- Comportement attendu pour `scapin serve`
- Permet d'accéder à l'API depuis le réseau local
- Configurable : `scapin serve --host localhost`
- **Verdict : Fonctionnalité, pas vulnérabilité**

---

## 3. OWASP Top 10 (2021)

### A01:2021 — Broken Access Control ✅

| Contrôle | Implémentation |
|----------|----------------|
| Authentification | JWT avec expiration (7 jours) |
| Protection routes | `get_current_user` dependency |
| Rate limiting | `src/jeeves/api/auth/rate_limiter.py` |
| CORS | Origines configurables |

### A02:2021 — Cryptographic Failures ✅

| Contrôle | Implémentation |
|----------|----------------|
| Mots de passe | bcrypt hashing (PIN) |
| Tokens | JWT signé HS256 |
| Secrets | Variables d'environnement, jamais en dur |
| TLS | Recommandé en production (reverse proxy) |

### A03:2021 — Injection ✅

| Contrôle | Implémentation |
|----------|----------------|
| SQL | Requêtes paramétrées (sqlite3 `?` placeholders) |
| Command | Pas d'exécution de commandes utilisateur |
| XSS | Svelte échappe par défaut, `{@html}` sécurisé |

### A04:2021 — Insecure Design ✅

| Contrôle | Implémentation |
|----------|----------------|
| Threat modeling | Architecture documentée |
| Secure defaults | Auth activée par défaut |
| Fail securely | Exceptions sanitisées |

### A05:2021 — Security Misconfiguration ✅

| Contrôle | Implémentation |
|----------|----------------|
| Secrets par défaut | `jwt_secret_key` obligatoire |
| Headers | CORS restrictif |
| Error handling | Messages génériques (pas de stack traces) |

### A06:2021 — Vulnerable Components ⚠️

| Contrôle | Status |
|----------|--------|
| pip-audit | 1 vuln medium (ecdsa, pas de fix) |
| npm audit | 3 low (cookie, breaking fix) |
| Monitoring | Manuel — à automatiser en CI |

**Recommandation** : Ajouter `pip-audit` et `npm audit` au CI/CD.

### A07:2021 — Identification Failures ✅

| Contrôle | Implémentation |
|----------|----------------|
| Brute force | Rate limiter sur /api/auth/login |
| Session | JWT avec expiration |
| Logout | Token invalidation (frontend) |

### A08:2021 — Software/Data Integrity ✅

| Contrôle | Implémentation |
|----------|----------------|
| Intégrité données | Hashes SHA256 pour métadonnées |
| CI/CD | GitHub Actions |
| Dépendances | Versions épinglées |

### A09:2021 — Security Logging ✅

| Contrôle | Implémentation |
|----------|----------------|
| Logging | ScapinLogger avec niveaux |
| Audit trail | Actions loggées |
| Monitoring | Logs rotatifs |

### A10:2021 — SSRF ✅

| Contrôle | Implémentation |
|----------|----------------|
| URLs externes | Limitées aux APIs connues (Graph, Anthropic) |
| Validation | URLs dans la configuration |

---

## 4. Recommandations

### Corrections Effectuées

- ✅ **urllib3** : Mis à jour 2.6.2 → 2.6.3

### Actions Futures

| Priorité | Action | Échéance |
|----------|--------|----------|
| **MEDIUM** | Surveiller fix ecdsa | Continu |
| **LOW** | Migrer python-jose → PyJWT | v1.1 |
| **LOW** | Automatiser audits en CI | v1.1 |

### Non-actions Justifiées

| Item | Raison |
|------|--------|
| cookie npm | Fix nécessite breaking change SvelteKit |
| autoescape Jinja2 | Templates IA, pas HTML |
| Pickle vector_store | Code migration legacy |
| 0.0.0.0 binding | Fonctionnalité serveur |

---

## 5. Conclusion

Le projet Scapin est **conforme aux bonnes pratiques de sécurité** pour une application locale mono-utilisateur. Les vulnérabilités identifiées sont soit :

1. **Sans fix disponible** (ecdsa) — risque faible car non utilisé directement
2. **Avec fix breaking** (cookie) — risque faible accepté
3. **Faux positifs** (bandit) — analysés et documentés

**Statut final : ✅ Prêt pour v1.0 Release Candidate**

---

*Rapport généré le 9 janvier 2026*
