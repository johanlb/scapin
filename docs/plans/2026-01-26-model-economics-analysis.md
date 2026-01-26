# Analyse Économique des Modèles IA — Scapin

**Date** : 26 janvier 2026
**Statut** : Document de référence
**Contexte** : Brainstorming architecture des prompts

---

## Tarification comparée (janvier 2026)

### Anthropic

| Modèle | Input $/M | Output $/M | Ratio vs Haiku | Notes |
|--------|-----------|------------|----------------|-------|
| Haiku 3.5 | $0.80 | $4.00 | 1x | Rapide, bon JSON |
| Sonnet 3.5 | $3.00 | $15.00 | ~4x | Équilibré, excellent écriture |
| Opus 3 | $15.00 | $75.00 | ~19x | Raisonnement profond |

*Avec prompt caching : input Haiku = $0.08/M (90% réduction)*

### OpenAI

| Modèle | Input $/M | Output $/M | Notes |
|--------|-----------|------------|-------|
| GPT-4o mini | $0.15 | $0.60 | **Ultra cheap**, bon général |
| GPT-4o | $2.50 | $10.00 | Multimodal, rapide |
| o1-mini | $3.00 | $12.00 | Raisonnement, math |
| o1-preview | $15.00 | $60.00 | Raisonnement complexe |

### Mistral

| Modèle | Input $/M | Output $/M | Notes |
|--------|-----------|------------|-------|
| Small | $0.20 | $0.60 | Très cheap, hébergement EU |
| Medium | $2.70 | $8.10 | Bon rapport qualité/prix |
| Large | $4.00 | $12.00 | Performant |

### Google

| Modèle | Input $/M | Output $/M | Notes |
|--------|-----------|------------|-------|
| Gemini Flash | $0.075 | $0.30 | **Le moins cher du marché** |
| Gemini Pro | $3.50 | $10.50 | Long contexte (1M tokens) |

---

## Coût par email type (10k input, 1.5k output)

| Modèle | Coût/email | Ratio vs moins cher |
|--------|------------|---------------------|
| Gemini Flash | $0.001 | 1x |
| GPT-4o mini | $0.002 | 2x |
| Mistral Small | $0.003 | 3x |
| Haiku 3.5 | $0.014 | 14x |
| o1-mini | $0.048 | 48x |
| GPT-4o | $0.040 | 40x |
| Sonnet 3.5 | $0.067 | 67x |
| Opus 3 | $0.263 | 263x |

---

## Impact de l'escalade

L'escalade est le facteur de coût dominant, pas le nombre de tokens.

| Scénario | Coût email |
|----------|------------|
| Haiku réussit | $0.014 |
| Escalade → Sonnet | $0.081 (6x) |
| Escalade → Opus | $0.277 (20x) |

**Règle** : Réduire le taux d'escalade de 10% → 5% économise plus que réduire les tokens de 30%.

---

## Modèle optimal par mission

| Mission | Besoins | Modèle recommandé | Alternative | Coût |
|---------|---------|-------------------|-------------|------|
| **Extraction simple** | Entités, JSON | GPT-4o mini | Gemini Flash | $0.002 |
| **Extraction + contexte** | Compréhension PKM | GPT-4o mini | Haiku | $0.002 |
| **Raisonnement/décision** | Logique, priorisation | o1-mini | Sonnet | $0.048 |
| **Écriture/retouche** | Style, Markdown | Sonnet | GPT-4o | $0.067 |
| **Arbitrage critique** | Nuances, jugement | Sonnet | o1-preview | $0.067 |
| **Cas extrême** | Complexité maximale | Opus | o1-preview | $0.263 |

---

## Comparaison architectures (100 emails)

### Architecture actuelle (4 passes Haiku, aveugle → enrichi)

| Composant | Coût |
|-----------|------|
| 4 passes Haiku × 100 | $3.44 |
| Escalade 10% Sonnet | $0.60 |
| **Total** | **$4.04** |

### Architecture Context-First mono-modèle (Haiku)

| Composant | Coût |
|-----------|------|
| 70 simples (1 passe) | $0.98 |
| 25 moyens (2 passes) | $0.70 |
| 5 complexes (Sonnet) | $0.30 |
| **Total** | **$1.98** (-51%) |

### Architecture Multi-modèle optimisée

| Composant | Modèle | Coût |
|-----------|--------|------|
| 70 simples | GPT-4o mini | $0.14 |
| 25 moyens | o1-mini | $1.05 |
| 5 complexes | Sonnet | $0.34 |
| **Total** | | **$1.53** (-62%) |

### Architecture tout Sonnet

| Composant | Coût |
|-----------|------|
| 100 emails × Sonnet | $6.70 |
| Qualité maximale | +66% vs actuel |

### Architecture tout Opus

| Composant | Coût |
|-----------|------|
| 100 emails × Opus | $22.50 |
| **Non justifié économiquement** | +457% vs actuel |

---

## Recommandations

### Pour l'analyse d'événements

1. **Utiliser le contexte PKM dès le départ** — l'analyse aveugle n'apporte pas de valeur
2. **Router par complexité** plutôt que par étape d'analyse
3. **Considérer GPT-4o mini pour l'extraction** — 6x moins cher que Haiku pour qualité comparable
4. **Réserver Sonnet/Opus pour les décisions critiques**

### Pour la retouche

1. **Sonnet reste optimal** — qualité d'écriture inégalée
2. **Injecter le Canevas** — actuellement absent (gap critique)

### Risques multi-fournisseur

| Risque | Mitigation |
|--------|------------|
| Complexité technique | Abstraction via AI Router existant |
| Formats différents | Validation JSON stricte |
| Latence variable | Timeout + fallback |
| Disponibilité | Fallback automatique |
| Données sensibles | Option Mistral (EU) pour données critiques |

---

## Impact du Chat Assistant

L'ajout d'un assistant chat avec RAG est économiquement très acceptable.

### Coût chat avec RAG (usage modéré : 50 questions/mois)

| Type de question | Volume | Coût unitaire | Total |
|------------------|--------|---------------|-------|
| Questions simples (factuel) | 30 | $0.03 | $0.90 |
| Questions moyennes (analyse) | 15 | $0.10 | $1.50 |
| Questions stratégiques (Opus) | 5 | $0.25 | $1.25 |
| **Total** | 50 | | **~$3.65/mois** |

### Conclusion chat

Avec RAG (contexte PKM injecté), le chat cloud Sonnet est **très abordable** — environ $2.50-5/mois pour un usage modéré. Le modèle local n'est pas nécessaire pour cette raison économique.

---

## Projections Haute Capacité

### Volume cible (usage complet Scapin)

| Source | Volume/jour | Volume/mois | Caractéristiques |
|--------|-------------|-------------|------------------|
| Teams | 200 | 6 000 | Messages courts, conversations |
| Emails (pro + perso) | 200 | 6 000 | Variable, threads |
| WhatsApp | 30 | 900 | Personnel, informel |
| Transcriptions | 5 | 150 | Long (10-60 min), dense |
| **Total** | **435** | **~13 000** | |

### Architecture multi-tier et coûts

| Niveau | Description | Volume | Coût unitaire | Total |
|--------|-------------|--------|---------------|-------|
| 0 | Pré-filtrage (règles) | 13 000 | $0 | $0 |
| — | Agrégation (threads) | 6 500 → 3 000 | $0 | $0 |
| 1 | Haiku triage (80%) | 2 400 | $0.004 | $9.60 |
| 2a | Sonnet analyse (20%) | 600 | $0.025 | $15.00 |
| 2b | Sonnet transcriptions | 150 | $0.15 | $22.50 |
| 3 | Opus stratégique | 20 | $0.25 | $5.00 |
| — | Retouche notes | 200 | $0.05 | $10.00 |
| — | Chat assistant | 500 | $0.05 | $25.00 |
| — | Embeddings (re-index) | 1 000 | $0.001 | $1.00 |
| | **Sous-total** | | | **$88.10** |
| | Marge sécurité (+30%) | | | $26.40 |
| | **TOTAL MENSUEL** | | | **~$117** |

### Conclusion haute capacité

Avec l'architecture multi-tier :
- **Pré-filtre** : 50% du volume éliminé sans IA
- **Agrégation** : Messages groupés en conversations
- **Haiku (cached)** : 80% traité rapidement et à bas coût
- **Sonnet** : 20% complexes + transcriptions

**13 000 événements/mois → ~$117/mois** (bien dans le budget de $200)

---

## Architecture Cloud + RAG Recommandée

Voir le document principal : [Architecture Modulaire des Prompts](./2026-01-26-prompt-architecture-design.md)

**Résumé** :

| Niveau | Modèle | Usage | Coût |
|--------|--------|-------|------|
| Triage | Haiku (cached) | 80% des events | $0.004 |
| Analyse | Sonnet | 20% complexes + retouche | $0.025-0.05 |
| Stratégique | Opus | Décisions critiques | $0.25 |

**Coût mensuel estimé** :
- Usage actuel (~1000 emails) : ~$30-40/mois
- Usage haute capacité (~13 000 events) : ~$117/mois

---

## Questions ouvertes

1. **Seuils d'escalade** : 85% de confiance est-il le bon seuil Haiku → Sonnet ?
2. **Agrégation Teams** : Quelle fenêtre temporelle optimale ? (5 min ? 30 min ?)
3. **Transcriptions** : Prompt spécialisé ou pipeline standard ?
4. **Monitoring** : Alerter à quel seuil de coût ? ($100 ? $150 ?)

---

*Document créé lors du brainstorming du 26 janvier 2026 — v2 avec projections haute capacité*
