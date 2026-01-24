---
name: workflow
description: Méthodologie Scapin-Clean - Standards de qualité, checklist de fin de tâche, conventions de commit. Utiliser avant de committer ou pour vérifier la conformité du code.
allowed-tools: Bash, Read, Grep
---

# Méthodologie Scapin-Clean

Standards de qualité et workflow pour le développement Scapin.

## Checklist Avant Commit

**→ La checklist BLOQUANTE de référence est dans `CLAUDE.md` section "Discipline de Livraison".**

Résumé rapide :
- Documentation mise à jour (technique + user guide si besoin)
- Tests E2E pour UI, unitaires pour backend
- Test manuel effectué et décrit
- Ruff 0 warning, TypeScript check passe
- Pas de TODO, code commenté, console.log

## Conventions de Commit

Format : `type(scope): description`

**Types :**
| Type | Usage |
|------|-------|
| `feat` | Nouvelle fonctionnalité |
| `fix` | Correction de bug |
| `refactor` | Refactoring sans changement fonctionnel |
| `docs` | Documentation uniquement |
| `test` | Ajout/modification de tests |
| `chore` | Maintenance, dépendances |

**Exemples :**
```
feat(sancho): add multi-pass convergence logic
fix(api): handle null multi_pass in queue response
refactor(valets): rename Jeeves to Frontin
docs: update session notes
test(e2e): fix flaky selectors
```

## Commandes

```bash
# Développement
./scripts/dev.sh                      # Backend + Frontend

# Tests
.venv/bin/pytest tests/ -v            # Backend unitaires
cd web && npx playwright test         # E2E complets
cd web && npx playwright test --ui    # E2E avec UI debug

# Qualité
.venv/bin/ruff check src/ --fix       # Lint Python + autofix
cd web && npm run check               # Types TypeScript

# CLI Scapin
python scapin.py --help
```

## Structure du Projet

```
scapin/
├── src/
│   ├── trivelin/       # Perception & triage
│   ├── sancho/         # Raisonnement IA
│   ├── passepartout/   # Base de connaissances
│   ├── planchet/       # Planification
│   ├── figaro/         # Orchestration
│   ├── sganarelle/     # Apprentissage
│   ├── frontin/        # API & CLI
│   └── core/           # Infrastructure partagée
├── web/                # Frontend SvelteKit
├── tests/              # Tests backend
└── docs/               # Documentation
    └── user-guide/     # Guide utilisateur (specs)
```

## Fichiers Critiques

**Ne pas modifier sans review (demander à Johan) :**

| Fichier | Rôle |
|---------|------|
| `src/trivelin/v2_processor.py` | Pipeline Multi-Pass v2.2 |
| `src/sancho/multi_pass_analyzer.py` | Convergence IA |
| `src/passepartout/note_manager.py` | Gestion notes |
| `src/core/config_manager.py` | Configuration globale |

## Qualité du Code

### Python (Ruff)
- 0 warning toléré
- Type hints obligatoires
- Docstrings pour fonctions publiques

### TypeScript/Svelte
- `npm run check` doit passer
- Types explicites, pas de `any`
- Svelte 5 runes : `$state`, `$derived`, `$effect`

### Tests
- Couverture backend : 95%+
- Tests E2E : 100% pass rate
- **Tester les cas d'erreur**, pas seulement le happy path
