---
name: workflow
description: Méthodologie Scapin-Clean - Standards de qualité, checklist de fin de tâche, conventions de commit. Utiliser avant de committer ou pour vérifier la conformité du code.
allowed-tools: Bash, Read, Grep
---

# Méthodologie Scapin-Clean

Standards de qualité et workflow pour le développement Scapin.

## Principes Fondamentaux

1. **Évaluation** : Demander confirmation avant de modifier des fichiers critiques
2. **Atomicité** : Un commit par fonctionnalité ou correction cohérente
3. **Qualité** : 0 warning Ruff toléré. Type hints obligatoires
4. **Information en couches** : Résumés actionnables (L1) avant détails techniques (L3)

## Commandes Rapides

```bash
# Développement (Backend + Frontend)
./scripts/dev.sh

# Tests backend
.venv/bin/pytest tests/ -v

# Tests E2E
cd web && npx playwright test

# Qualité du code
.venv/bin/ruff check src/ --fix
cd web && npm run check

# CLI Scapin
python scapin.py --help
```

## Checklist de Fin de Tâche

Avant chaque commit, vérifier :

- [ ] Tests backend passent : `.venv/bin/pytest tests/ -v`
- [ ] Types frontend OK : `cd web && npm run check`
- [ ] Ruff sans warnings : `.venv/bin/ruff check src/`
- [ ] CLAUDE.md à jour si changement significatif

## Conventions de Commit

Format : `type(scope): description`

**Types :**
- `feat` : Nouvelle fonctionnalité
- `fix` : Correction de bug
- `refactor` : Refactoring sans changement fonctionnel
- `docs` : Documentation uniquement
- `test` : Ajout/modification de tests
- `chore` : Maintenance, dépendances

**Exemples :**
```
feat(sancho): add multi-pass convergence logic
fix(api): handle null multi_pass in queue response
refactor(valets): rename Jeeves to Frontin
docs: update session notes
test(e2e): fix flaky selectors
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
```

## Fichiers Critiques

Ne pas modifier sans review :
- `src/trivelin/v2_processor.py` : Pipeline v2.2
- `src/sancho/multi_pass_analyzer.py` : Convergence IA
- `src/passepartout/note_manager.py` : Gestion notes
- `src/core/config_manager.py` : Configuration

## Qualité du Code

### Python (Ruff)
- 0 warning toléré
- Type hints obligatoires
- Docstrings pour fonctions publiques

### TypeScript/Svelte
- `npm run check` doit passer
- Types explicites, pas de `any`

### Tests
- Couverture backend : 95%+
- Tests E2E : 100% pass rate
