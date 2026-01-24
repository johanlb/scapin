# CLAUDE.md — Scapin

**Version** : v3.2 | **Stack** : Python 3.13 · Svelte 5 · SQLite · FAISS

---

## Mission

Scapin est le **gardien cognitif** de Johan. Il transforme emails et informations
en connaissances organisées via analyse IA multi-pass et mémoire contextuelle.

*"Prendre soin de Johan mieux que Johan lui-même."*

---

## Skills — Quand les Invoquer

| Skill | Invocation | Trigger |
|-------|------------|---------|
| **Valets** | `/valets` | "Où implémenter X ?", "Comment fonctionne Y ?" |
| **Session** | `/session` | "Qu'est-ce qui a été fait ?", début de session |
| **Workflow** | `/workflow` | Conventions de commit, commandes détaillées |
| **Debug** | `/debug` | "Ça ne marche pas", erreurs, diagnostic, logs |

---

## Contexte Johan

- **Langue** : Français (réponses, commentaires, commits)
- **Style** : Direct, concis, technique. Pas d'émojis sauf si demandé
- **Préférences** :
  - Proposer des options plutôt qu'imposer
  - Justifier les choix techniques
  - Atomicité des commits
  - 0 warning toléré (Ruff, TypeScript)

---

## Stack Technique

| Couche | Technologie | Notes |
|--------|-------------|-------|
| Backend | Python 3.13, FastAPI | venv : `.venv/` |
| Frontend | SvelteKit 2, Svelte 5 | Runes ($state, $derived) |
| Database | SQLite | `data/scapin.db` |
| Vectors | FAISS | `data/faiss/` |
| IA | Claude (Haiku → Sonnet → Opus) | Escalade automatique |
| Tests | pytest, Playwright | 95%+ backend, E2E |

---

## Fichiers Critiques

**Ne pas modifier sans confirmation explicite de Johan :**

| Fichier | Rôle |
|---------|------|
| `src/trivelin/v2_processor.py` | Pipeline Multi-Pass v2.2 |
| `src/sancho/multi_pass_analyzer.py` | Convergence IA |
| `src/passepartout/note_manager.py` | Gestion notes |
| `src/core/config_manager.py` | Configuration globale |

---

## Discipline de Livraison

### Documentation Obligatoire

**RÈGLE : Ne jamais livrer de code sans mettre à jour la documentation.**

| Type de changement | Documentation à mettre à jour |
|--------------------|-------------------------------|
| Nouveau comportement utilisateur | `docs/user-guide/` |
| Modification de workflow existant | `docs/user-guide/` + specs concernées |
| Nouvelle API / endpoint | `ARCHITECTURE.md` + types |
| Nouveau composant complexe | JSDoc/docstring dans le code |
| Changement d'architecture | `ARCHITECTURE.md` |

Si tu ne sais pas où documenter → **demande avant de coder**.

### Tests Obligatoires

**RÈGLE : Tester comme un utilisateur, pas comme un développeur.**

| Type de modification | Tests requis |
|----------------------|--------------|
| Fonctionnalité UI | Test E2E Playwright (parcours utilisateur complet) |
| Logique backend | pytest unitaire + intégration |
| Correction de bug | Test de non-régression prouvant le fix |
| Performance critique | Benchmark avant/après documenté |

Les tests doivent simuler le comportement réel de l'utilisateur, pas juste vérifier que le code compile.

### Validation par les Logs (PROACTIVE)

**Après toute modification backend, je dois consulter les logs pour valider.**

```bash
# Lancer avec logs visibles
python scapin.py --verbose process

# Vérifier absence d'erreurs dans les logs JSON
grep -E "(ERROR|WARNING)" data/logs/*.json

# Logs en temps réel pendant dev
tail -f data/logs/processing_$(date +%Y-%m-%d).json
```

**Fichiers de logs :**
| Fichier | Contenu |
|---------|---------|
| `data/logs/processing_YYYY-MM-DD.json` | Historique traitement emails |
| `data/logs/calendar_YYYY-MM-DD.json` | Événements calendrier |
| Console `--verbose` | Debug en temps réel |

**Je dois proactivement :**
- Consulter les logs après chaque modification backend
- Vérifier qu'aucun ERROR/WARNING nouveau n'apparaît
- Utiliser `--verbose --log-format json` pour debug difficile
- Reporter les erreurs trouvées dans les logs à Johan

### Checklist Avant Commit (BLOQUANTE)

**Je dois explicitement valider chaque point avant de proposer un commit :**

```
□ Documentation technique mise à jour (ARCHITECTURE.md si nécessaire)
□ User guide mis à jour si comportement utilisateur modifié (docs/user-guide/)
□ Tests E2E écrits et passants pour tout changement UI
□ Tests unitaires écrits et passants pour tout changement backend
□ Logs vérifiés — aucun ERROR/WARNING nouveau (pour changements backend)
□ Test manuel effectué — décrire exactement ce qui a été vérifié
□ Ruff : 0 warning
□ TypeScript : npm run check passe
□ Pas de TODO, code commenté, ou console.log laissé
```

**Si un point n'est pas coché, je dois l'expliquer et obtenir l'accord de Johan.**

---

## Anti-patterns (NE JAMAIS FAIRE)

| Anti-pattern | Pourquoi c'est un problème |
|--------------|---------------------------|
| **Tests "happy path" uniquement** | Les bugs sont dans les cas limites et erreurs |
| **console.log en production** | Utiliser le logger structuré |
| **`any` en TypeScript** | Perte totale de type safety |
| **Commit sans test manuel** | Le code "qui compile" != code qui fonctionne |
| **Plusieurs fonctionnalités par commit** | Impossible à reverter proprement |
| **Documenter "après"** | "Après" n'arrive jamais |
| **Modifier un fichier critique sans demander** | Risque de casser le pipeline |
| **Laisser du code commenté** | Pollue le codebase, Git garde l'historique |

---

## Gestion de Session

### Prévenir la Dégradation

- **Compacter régulièrement** : utiliser `/compact` quand le contexte devient lourd
- **Sessions focalisées** : une fonctionnalité majeure = une session
- **Documenter en cours de route** : ne pas attendre la fin pour écrire la doc

### En Début de Session

1. Consulter `/session` pour le contexte récent
2. Identifier les fichiers de doc à mettre à jour dès le départ
3. Planifier les tests AVANT de coder

### Signaux de Dégradation

Si je commence à :
- Oublier des détails mentionnés plus tôt
- Proposer des solutions incohérentes
- Faire des erreurs de syntaxe inhabituelles

→ Suggérer un `/compact` ou une nouvelle session.

---

## Commandes Essentielles

```bash
./scripts/dev.sh              # Tout démarrer
.venv/bin/pytest tests/ -v    # Tests backend
cd web && npm run check       # Types frontend
cd web && npx playwright test # Tests E2E
```

→ Plus de commandes et conventions de commit : `/workflow`

---

## Les 7 Valets (résumé)

| Valet | Module | Un mot |
|-------|--------|--------|
| Trivelin | `trivelin/` | Perception |
| Sancho | `sancho/` | Raisonnement |
| Passepartout | `passepartout/` | Mémoire |
| Planchet | `planchet/` | Planification |
| Figaro | `figaro/` | Orchestration |
| Sganarelle | `sganarelle/` | Apprentissage |
| Frontin | `frontin/` | Interface |

→ Détails et interactions : `/valets`

---

## Règles Critiques

1. **Confirmer avant de modifier** les fichiers critiques
2. **Un commit = une fonctionnalité** cohérente
3. **Checklist bloquante** — valider chaque point explicitement avant commit
4. **Documentation first** — si pas documenté, pas livré
5. **Skills avant implémentation** — consulter `/valets` pour savoir où coder
6. **Tester comme un utilisateur** — pas juste "ça compile"
7. **Consulter les logs** — vérifier proactivement après chaque modification backend
