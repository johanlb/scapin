# 10. Performance

Ce guide vous aide à comprendre les temps de réponse normaux de Scapin et à diagnostiquer les éventuelles lenteurs.

---

## Comportement Normal

### Temps de Réponse Attendus

| Opération | Temps normal | Notes |
|-----------|--------------|-------|
| **Chargement initial** | 2-5s | Dépend du nombre de notes |
| **Analyse email simple** | 3-8s | Email court, peu de contexte |
| **Analyse email complexe** | 15-45s | Multi-pass avec escalade Opus |
| **Recherche notes** | < 500ms | Recherche sémantique FAISS |
| **Briefing matinal** | 10-30s | Agrégation emails + calendrier |
| **Retouche note** | 5-15s | Enrichissement IA |

### Facteurs de Variation

Le temps d'analyse dépend de plusieurs facteurs :

1. **Longueur de l'email** — Plus le contenu est long, plus l'analyse prend du temps
2. **Complexité du sujet** — Un email technique déclenche plus de passes
3. **Contexte disponible** — Plus de notes liées = plus de recherche
4. **Modèle IA utilisé** — Haiku (rapide) → Sonnet → Opus (précis mais lent)

### Indicateurs de Progression

Pendant une analyse longue, l'interface affiche :

- **Barre de progression** — Pourcentage d'avancement
- **Badge de complexité** — ⚡ Simple | 🔍 Modéré | 🧠 Complexe | 🏆 Expert
- **Nombre de passes** — "Pass 2/5" par exemple
- **Modèle actuel** — Haiku, Sonnet, ou Opus

> **Astuce** : Un badge 🧠 ou 🏆 indique une analyse approfondie — la lenteur est normale et bénéfique.

---

## Troubleshooting

### L'interface ne répond plus (freeze)

**Causes possibles :**
- Analyse IA en cours (normal si barre de progression visible)
- Connexion serveur perdue

**Solutions :**
1. Vérifier la barre de progression — si elle bouge, patience
2. Rafraîchir la page (F5 ou pull-to-refresh mobile)
3. Vérifier que le backend est actif : `curl http://localhost:8000/api/health`

### Les emails mettent trop de temps à charger

**Causes possibles :**
- Connexion IMAP lente
- Trop d'emails à synchroniser

**Solutions :**
1. Vérifier la connexion internet
2. Limiter le fetch : `pkm process --limit 5`
3. Vérifier les logs : `python scripts/view_errors.py --stats`

### La recherche de notes est lente

**Causes possibles :**
- Index FAISS non optimisé
- Trop de notes (> 1000)

**Solutions :**
1. Reconstruire l'index : `pkm notes rebuild-index`
2. Vérifier les stats : `pkm stats`

### Le briefing met plus de 30 secondes

**Causes possibles :**
- Beaucoup d'emails non traités
- Calendrier avec nombreux événements

**Solutions :**
1. Traiter les emails en attente d'abord
2. Réduire la période de briefing dans les paramètres

---

## Optimiser Son Usage

### Bonnes Pratiques

1. **Traiter régulièrement** — Éviter l'accumulation de centaines d'emails
2. **Utiliser les filtres** — Marquer les newsletters comme "éphémères"
3. **Organiser les notes** — Des tags clairs accélèrent la recherche contextuelle
4. **Fermer les onglets inutiles** — Libérer la mémoire navigateur

### Configuration Recommandée

| Paramètre | Valeur recommandée | Impact |
|-----------|-------------------|--------|
| Emails par batch | 10-20 | Équilibre vitesse/exhaustivité |
| Notes max contexte | 10 | Évite surcharge IA |
| Seuil convergence | 95% | Qualité vs vitesse |

### Heures Creuses

L'API Anthropic peut être plus rapide :
- **Matin tôt** (6h-8h) — Moins de trafic
- **Week-end** — Charge réduite

---

## Diagnostic

### Vérifier la Santé du Système

```bash
# Santé globale
pkm health

# État de la queue
pkm queue

# Statistiques
pkm stats
```

### Consulter les Logs

```bash
# Erreurs récentes
python scripts/view_errors.py --stats

# Logs en temps réel
tail -f data/logs/processing_$(date +%Y-%m-%d).json

# Logs verbose
pkm --verbose process --limit 1
```

### Métriques de Performance

Les logs contiennent des marqueurs `[PERF]` pour le diagnostic :

```json
{
  "event": "analysis_complete",
  "perf": {
    "total_ms": 12500,
    "passes": 3,
    "model_escalations": 1,
    "context_search_ms": 450,
    "api_wait_ms": 11200
  }
}
```

**Lecture des métriques :**
- `total_ms` — Temps total d'analyse
- `api_wait_ms` — Temps d'attente API (généralement 80%+ du total)
- `context_search_ms` — Recherche de notes contextuelles
- `passes` — Nombre d'itérations multi-pass

### Profiling Avancé (Développeurs)

Pour un diagnostic approfondi avec flamegraph :

```bash
# Installer py-spy
pip install py-spy

# Générer un flamegraph pendant le traitement
py-spy record -o profile.svg --pid $(pgrep -f "uvicorn") --duration 60
```

Le fichier SVG montre visuellement où le temps CPU est consommé.

---

## Architecture Performance

### Optimisations Actives

Scapin intègre plusieurs optimisations :

| Optimisation | Bénéfice |
|--------------|----------|
| **Cache contexte** | -70% temps recherche (requêtes répétées) |
| **Early-stop éphémères** | Skip 30% emails (newsletters, OTP) |
| **Thread pool optimisé** | -75% overhead parallélisation |
| **Batch embeddings** | Moins d'appels API pour recherches multiples |

### Bottleneck Principal

> **Important** : ~80% du temps d'analyse = attente API Anthropic (I/O réseau).

Les optimisations backend ont un impact limité sur la latence perçue. Le temps d'attente IA est incompressible et représente le coût d'une analyse de qualité.

---

## Prochaines Étapes

- [8. Dépannage](08-troubleshooting.md) — Erreurs courantes et solutions
- [7. Configuration](07-configuration.md) — Ajuster les paramètres
