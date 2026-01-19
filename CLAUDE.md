# CLAUDE.md — Scapin

**Version** : v1.0.0-rc.1 | **Projet** : [github.com/johanlb/scapin](https://github.com/johanlb/scapin)

---

## Vision

Scapin est un **gardien cognitif personnel** avec une architecture inspirée du raisonnement humain. Il transforme le flux d'emails et d'informations en connaissances organisées via une analyse IA multi-pass, une mémoire contextuelle et une planification d'actions intelligente.

**Mission** : *"Prendre soin de Johan mieux que Johan lui-même."*

---

## Skills Disponibles

| Skill | Invocation | Usage |
|-------|------------|-------|
| **Valets** | `/valets` | Architecture cognitive, modules, où implémenter |
| **Session** | `/session` | Notes de session, historique récent |
| **Workflow** | `/workflow` | Standards qualité, checklist, conventions |

---

## Quick Reference

### Commandes

```bash
./scripts/dev.sh              # Dev (Backend + Frontend)
.venv/bin/pytest tests/ -v    # Tests
.venv/bin/ruff check src/     # Lint
cd web && npm run check       # Types frontend
```

### Les 7 Valets

| Valet | Rôle | Module |
|-------|------|--------|
| Trivelin | Perception & triage | `src/trivelin/` |
| Sancho | Raisonnement IA | `src/sancho/` |
| Passepartout | Base de connaissances | `src/passepartout/` |
| Planchet | Planification | `src/planchet/` |
| Figaro | Orchestration | `src/figaro/` |
| Sganarelle | Apprentissage | `src/sganarelle/` |
| Frontin | API & CLI | `src/frontin/` |

---

## Documents de Référence

| Document | Rôle |
|----------|------|
| [DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md) | Fondation - l'âme du projet |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technique v1.0 |
| [README.md](README.md) | Vue d'ensemble |
| [User Guide](docs/user-guide/README.md) | Manuel utilisateur |

---

## Principes de Travail

1. **Évaluation** : Confirmer avant de modifier des fichiers critiques
2. **Atomicité** : Un commit = une fonctionnalité cohérente
3. **Qualité** : 0 warning Ruff, type hints obligatoires
4. **Checklist** : Tests + lint avant commit
