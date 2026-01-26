# Analyse d'Alignement des Plans

**Date** : 27 janvier 2026
**Objectif** : Aligner tous les plans avec le code existant et CLAUDE.md

---

## Résumé Exécutif

| Phase | Plan | État Code | Verdict |
|-------|------|-----------|---------|
| 0.1 | Migration note_id | ❌ Pas implémenté | À faire |
| 0.2 | Prompt Caching | ✅ Déjà implémenté | Vérifier usage |
| 0.3 | Canevas dans Retouche | ❌ Pas implémenté | À faire |
| 1 | Grimaud Guardian | ❌ Pas implémenté | À faire |
| 5 | Chat + Mémoire | ❌ Pas implémenté | Optionnel |
| 5 | Bazin Briefings | ❌ Pas implémenté | Optionnel |
| 5 | OmniFocus | ❌ Pas implémenté | Optionnel |

---

## Phase 0 — Fondations

### 0.1 Migration note_id

**Plan** : `migration-note-id-format.md`
**État** : Non implémenté

| Aspect | Détail |
|--------|--------|
| Problème | 14 collisions de noms (notes différentes, même filename) |
| Solution | Passer de `filename` à `path/filename` comme identifiant |
| Phases | 6 phases détaillées dans le plan |
| Fichiers critiques | `note_manager.py`, `note_metadata.py` (requiert confirmation Johan) |

**Verdict** : Plan complet, prêt à implémenter.

---

### 0.2 Prompt Caching

**Plan** : `prompt-architecture-design.md` (section "Prompt Caching")
**État** : ✅ Déjà implémenté dans le code

**Code existant** :

```python
# src/sancho/router.py:646-724
def _call_claude_with_cache(
    self,
    user_prompt: str,
    system_prompt: str,
    model: AIModel,
    max_tokens: int = 2048,
) -> tuple[Optional[str], dict]:
    """Call Claude API with prompt caching enabled."""
    message = self._client.messages.create(
        model=model.value,
        max_tokens=max_tokens,
        system=[{
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},  # ← Cache activé
        }],
        messages=[{"role": "user", "content": user_prompt}],
    )
```

**Utilisations** :
- `src/sancho/analysis_engine.py:178` — Retouche
- `src/sancho/multi_pass_analyzer.py:863` — Pipeline analyse emails

**Verdict** : Tâche Phase 0.2 est **complète**. Le prompt caching fonctionne déjà.
→ Mettre à jour master-roadmap.md pour refléter cet état.

---

### 0.3 Injecter Canevas dans Retouche

**Plan** : `prompt-architecture-design.md` (section "Canevas")
**État** : ❌ Gap identifié — Canevas existe mais n'est PAS injecté dans Retouche

**Code existant** :

```python
# src/passepartout/context_loader.py — Canevas loader ✅ existe
class ContextLoader:
    def load_context(self) -> str:
        """Load and concatenate all valid canevas files."""
        # Charge Profile.md, Projects.md, Goals.md, Preferences.md
```

```python
# src/sancho/router.py:142-148 — ContextLoader utilisé dans AIRouter ✅
self.context_loader = ContextLoader()

# src/passepartout/retouche_reviewer.py — ❌ N'importe PAS ContextLoader
from src.sancho.analysis_engine import AnalysisEngine  # OK
# Pas d'import de context_loader !
```

**Gap** : `retouche_reviewer.py` utilise `AnalysisEngine` mais ne charge pas le Canevas.
L'IA de retouche n'a donc pas le contexte Johan (objectifs, projets, préférences).

**Solution** :
1. Injecter le Canevas comme `system_prompt` dans les appels retouche
2. Modifier `RetoucheReviewer` pour accepter un `ContextLoader`

**Verdict** : Tâche Phase 0.3 à implémenter.

---

## Phase 1 — Grimaud Guardian

**Plan** : `grimaud-guardian-design.md`
**État** : Non implémenté

| Aspect | Détail |
|--------|--------|
| Module | Nouveau `src/grimaud/` (4 fichiers) |
| Rôle | Gardien proactif du PKM (remplace Retouche pour la maintenance) |
| Dépendances | Passepartout (notes, FAISS), Sancho (IA), Frontin (API) |

**Attention** : Le plan dit "Grimaud remplace Retouche" mais Retouche existe déjà avec beaucoup de code.
→ Clarifier : Grimaud **englobe** Retouche ou bien ils coexistent ?

**Fichiers Retouche existants** :
- `src/passepartout/retouche_reviewer.py` — 1200+ lignes
- `src/passepartout/note_scheduler.py` — Scheduling SM-2
- `src/passepartout/note_types.py` — Types de notes

**Verdict** : Plan validé. Clarifier la relation Grimaud/Retouche avant implémentation.

---

## Phase 5 — Nice-to-have

### Chat + Mémoire

**Plan** : `chat-memory-design.md`
**État** : Non implémenté

| Aspect | Détail |
|--------|--------|
| Module | `src/frontin/chat/` (nouveau) |
| Tables | `chat_memories` (nouveau) |
| API | `/api/chat/*` (nouveau) |
| UI | `ChatPanel.svelte` (nouveau) |

**Verdict** : Plan complet, optionnel.

---

### Bazin Briefings

**Plan** : `bazin-proactivity-design.md`
**État** : Non implémenté

| Aspect | Détail |
|--------|--------|
| Module | `src/bazin/` (nouveau) |
| Rôle | 9ème valet — Préparation & Anticipation |
| Dépendances | Calendrier (iCloud), PKM, OmniFocus |

**Verdict** : Plan complet, optionnel.

---

### OmniFocus Integration

**Plan** : `omnifocus-integration-design.md`
**État** : Non implémenté

| Aspect | Détail |
|--------|--------|
| Module | `src/trivelin/omnifocus/` (nouveau) |
| API | OmniFocus Automation (JavaScript bridge) |
| Prérequis | OmniFocus Pro |

**Verdict** : Plan complet, optionnel.

---

## Incohérences Détectées

### 1. CLAUDE.md — Liste des valets obsolète

**Problème** : CLAUDE.md liste 7 valets, mais Grimaud et Bazin en ajoutent 2.

```markdown
# Actuel (CLAUDE.md)
| Valet | Module | Un mot |
| Trivelin | `trivelin/` | Perception |
| Sancho | `sancho/` | Raisonnement |
| Passepartout | `passepartout/` | Mémoire |
| Planchet | `planchet/` | Planification |
| Figaro | `figaro/` | Orchestration |
| Sganarelle | `sganarelle/` | Apprentissage |
| Frontin | `frontin/` | Interface |
```

**Solution** : Ajouter Grimaud et Bazin après implémentation Phase 1.

---

### 2. master-roadmap.md — Prompt caching "À activer"

**Problème** : Le roadmap dit "Activer prompt caching (-50% coût)" mais c'est déjà fait.

**Solution** : Mettre à jour master-roadmap.md :
- Phase 0.2 → "Vérifier utilisation prompt caching"
- Ajouter note : "Implémenté dans router.py:_call_claude_with_cache()"

---

### 3. Grimaud vs Retouche — DÉCIDÉ

**Décision Johan (27/01/2026)** : Option A — Grimaud **englobe** Retouche progressivement.

**Implication** :
- Le code de `retouche_reviewer.py` migrera vers `src/grimaud/`
- Le système SM-2 sera intégré dans Grimaud
- Migration progressive pour ne pas casser le fonctionnement existant

---

## Recommandations

### Ordre d'implémentation Phase 0

1. **0.3 Canevas dans Retouche** (rapide, ~1h)
   - Injecter `ContextLoader` dans `RetoucheReviewer`
   - Test : vérifier que le system prompt contient le canevas

2. **0.1 Migration note_id** (complexe, ~1-2 jours)
   - Suivre les 6 phases du plan
   - Demander confirmation Johan avant `note_manager.py`

3. ~~0.2 Prompt Caching~~ → Déjà fait

### Avant Phase 1 (Grimaud)

Clarifier avec Johan :
- Grimaud **remplace** Retouche complètement ?
- Ou bien Grimaud **ajoute** la maintenance proactive à côté de Retouche ?

---

## Prochaines Actions

1. [ ] Mettre à jour master-roadmap.md (prompt caching = fait)
2. [ ] Implémenter injection Canevas dans Retouche
3. [ ] Clarifier relation Grimaud/Retouche avec Johan
4. [ ] Commencer migration note_id (Phase 0.1)

---

*Document généré le 27 janvier 2026*
