# Bug #55 : L'option "Autre" ne déclenche pas de ré-analyse

**Date** : 10 janvier 2026
**Priorité** : CRITIQUE
**Statut** : Analyse et proposition de solution

---

## Problème constaté

### Scénario reproductible

1. L'utilisateur consulte un email dans la file de revue
2. L'IA propose : `archive → Archive/2025/Finance` (95% confiance)
3. L'utilisateur clique sur **"Autre"** et donne l'instruction :
   > "Classer dans Archive/2025/Relevés bancaires"
4. L'élément apparaît comme **"Action approuvée"** dans les traités
5. **BUG** : L'instruction utilisateur a été ignorée, l'action originale a été exécutée

### Comportement actuel (incorrect)

```
[Utilisateur] → Clique "Autre" + instruction
                        ↓
              [Backend] → Traite comme APPROVE de l'action originale
                        ↓
              [Email] → Déplacé vers Archive/2025/Finance (PAS Relevés bancaires)
```

### Comportement attendu

```
[Utilisateur] → Clique "Autre" + instruction
                        ↓
              [Backend] → Déclenche nouvelle analyse avec instruction
                        ↓
              [Nouvelle analyse] → Prend en compte l'instruction utilisateur
                        ↓
              [Email] → Déplacé selon la nouvelle analyse
```

---

## Proposition de solution

### Nouveau workflow "Autre"

Quand l'utilisateur clique sur "Autre" et soumet une instruction :

#### Option 1 : Analyse immédiate (bouton "Analyser maintenant")

```
┌─────────────────────────────────────────────────────────┐
│  Instruction utilisateur soumise                        │
│    ↓                                                     │
│  UI affiche "Analyse en cours..." (spinner)             │
│    ↓                                                     │
│  Backend déclenche nouvelle analyse avec instruction    │
│    ↓                                                     │
│  WebSocket → UI raffraîchie avec nouvelle analyse       │
│    ↓                                                     │
│  Utilisateur valide ou modifie la nouvelle proposition  │
└─────────────────────────────────────────────────────────┘
```

**UX** :
- L'élément reste à l'écran
- Spinner visible "Nouvelle analyse en cours..."
- Les actions sont désactivées pendant l'analyse
- Quand l'analyse arrive, l'UI se rafraîchit automatiquement
- L'utilisateur peut alors approuver/modifier/rejeter

#### Option 2 : Mise en file (bouton "Analyser plus tard")

```
┌─────────────────────────────────────────────────────────┐
│  Instruction utilisateur soumise                        │
│    ↓                                                     │
│  Élément déplacé à la FIN de la file de revue           │
│    ↓                                                     │
│  UI passe à l'élément suivant immédiatement             │
│    ↓                                                     │
│  Backend lance l'analyse en background                  │
│    ↓                                                     │
│  Quand analyse terminée → mise à jour de l'élément      │
│    ↓                                                     │
│  Utilisateur retrouvera l'élément avec nouvelle analyse │
└─────────────────────────────────────────────────────────┘
```

**UX** :
- Transition fluide vers l'élément suivant
- Toast "Élément mis en file pour ré-analyse"
- L'élément réapparaîtra plus tard avec la nouvelle analyse

---

## Implémentation technique

### 1. Nouveau endpoint API

```
POST /api/queue/{item_id}/reanalyze
{
    "user_instruction": "Classer dans Archive/2025/Relevés bancaires",
    "mode": "immediate" | "background"
}

Response:
{
    "success": true,
    "analysis_id": "...",
    "status": "analyzing" | "queued"
}
```

### 2. Injection de l'instruction dans le prompt

Ajouter dans `templates/ai/email_analysis.j2` :

```jinja2
{% if user_instruction %}
**INSTRUCTION DE L'UTILISATEUR :**
L'utilisateur a explicitement demandé : "{{ user_instruction }}"

⚠️ IMPORTANT : Cette instruction DOIT être prise en compte en priorité.
Adapte ta recommandation pour respecter cette demande tout en expliquant ton raisonnement.
{% endif %}
```

### 3. Modification du modèle QueueItem

```python
# Nouveaux champs
user_instruction: Optional[str] = None
reanalysis_count: int = 0
original_analysis: Optional[dict] = None  # Sauvegarder l'analyse initiale
```

### 4. Frontend - Nouveau modal "Autre"

```svelte
<!-- Modal amélioré pour "Autre" -->
<Modal title="Donner une instruction">
    <textarea bind:value={instruction} placeholder="Ex: Classer dans Archive/2025/Relevés bancaires" />

    <div class="flex gap-2 mt-4">
        <Button variant="primary" onclick={handleImmediateAnalysis} disabled={analyzing}>
            {analyzing ? 'Analyse en cours...' : 'Analyser maintenant'}
        </Button>
        <Button variant="secondary" onclick={handleQueuedAnalysis}>
            Analyser plus tard
        </Button>
        <Button variant="ghost" onclick={closeModal}>
            Annuler
        </Button>
    </div>
</Modal>
```

### 5. WebSocket event pour mise à jour

```typescript
// Nouveau type d'événement
interface ReanalysisCompleteEvent {
    type: 'reanalysis_complete';
    item_id: string;
    new_analysis: QueueItemAnalysis;
}
```

---

## Fichiers à modifier

### Backend

| Fichier | Modification |
|---------|--------------|
| `src/jeeves/api/routers/queue.py` | Ajouter endpoint `/reanalyze` |
| `src/jeeves/api/services/queue_service.py` | Ajouter `reanalyze_item()` |
| `src/jeeves/api/models/queue.py` | Ajouter `ReanalyzeRequest` |
| `templates/ai/email_analysis.j2` | Ajouter section instruction utilisateur |
| `src/trivelin/processor.py` | Supporter l'analyse avec instruction |

### Frontend

| Fichier | Modification |
|---------|--------------|
| `web/src/routes/flux/+page.svelte` | Nouveau modal "Autre" avec 2 boutons |
| `web/src/lib/api/queue.ts` | Ajouter `reanalyzeItem()` |
| `web/src/lib/stores/websocket.svelte.ts` | Gérer `reanalysis_complete` event |

---

## Estimation d'effort

| Tâche | Effort |
|-------|--------|
| API endpoint `/reanalyze` | 2h |
| Injection instruction dans prompt | 1h |
| UI modal amélioré | 2h |
| Mode "immediate" avec spinner | 2h |
| Mode "background" avec mise en file | 2h |
| WebSocket pour rafraîchissement | 1h |
| Tests | 2h |
| **Total** | **12h** |

---

## Métriques de succès

| Métrique | Objectif |
|----------|----------|
| Instructions "Autre" traitées correctement | 100% |
| Temps de ré-analyse (mode immédiat) | < 10s |
| Satisfaction utilisateur | Instruction respectée |

---

## Questions ouvertes

1. **Limite de ré-analyses** : Faut-il limiter le nombre de ré-analyses par item ? (Suggestion : max 3)

2. **Historique** : Conserver l'historique des analyses successives pour debug ?

3. **Apprentissage** : Utiliser les instructions "Autre" pour entraîner le modèle ? (Pattern learning)

---

*Document créé le 10 janvier 2026*
