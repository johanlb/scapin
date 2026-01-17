# Recommandations Stratégiques pour Scapin (Post-v1.0)

Basé sur l'analyse de l'architecture et de la philosophie du projet, voici les axes d'amélioration et les évolutions logiques que je suggère pour les phases à venir.

## 1. Robustesse Cognitive (Sancho v3)

L'architecture actuelle repose beaucoup sur un modèle unique (avec escalade). Pour atteindre une fiabilité "critique", il faut diversifier les "points de vue".

-   **[Phase 2.5] Consensus Multi-Modèles (Judge-Jury)** :
    -   Implémenter la **Passe 4** de Sancho telle que décrite mais non réalisée.
    -   *Idée* : Utiliser un modèle "Avocat du Diable" (ex: GPT-4o ou un modèle spécialisé prompté pour trouver des failles) qui critique la décision de Claude avant validation. Si le critique trouve une faille majeure, on escalade.
-   **Détection d'Hallucination par Cross-Checking** :
    -   Pour les extractions factuelles (dates, montants), faire une double extraction par un petit modèle rapide (Haiku) et comparer. Si divergence → Sonnet.

## 2. Performance & Latence (Réactivité)

Le multi-pass est puissant mais coûteux en temps.

-   **Exécution Spéculative** :
    -   Lancer la recherche de contexte (Passepartout) *en parallèle* de la Passe 1 (Analyse initiale). Si la Passe 1 confirme le besoin de contexte, il est déjà prêt.
    -   Gagner ~2-3 secondes sur le pipeline complet.
-   **Préchauffage Contextuel** :
    -   Quand un email arrive d'un VIP, pré-charger son contexte (dernières notes, résumé interactions) en cache avant même l'analyse.

## 3. Confidentialité & "Privacy firewall"

Le principe d'intimité totale est risqué si des données partent vers les API.

-   **Redaction Layer (PII Sanitization)** :
    -   Avant d'envoyer le contexte à une API (Anthropic), passer par une couche locale (regex ou petit modèle local type BERT/spacy) qui masque les données ultra-sensibles (numéros de sécu, codes bancaires explicites) si elles ne sont pas pertinentes pour l'action.
-   **Local-First Classification** :
    -   Utiliser un petit modèle local (ex: via Ollama ou un classifier scikit-learn entraîné sur l'historique) pour le tri trivial (spam, notifs) afin de ne rien envoyer au cloud pour 80% du volume inutile.

## 4. UX & Interaction (Jeeves)

-   **Boucle de Feedback Explicite** :
    -   Au lieu de juste corriger, Scapin devrait dire : *"J'ai remarqué que vous corrigez souvent mes brouillons pour ajouter des salutations plus formelles. Voulez-vous que j'ajuste mon ton par défaut pour ce contact ?"*
    -   Transformer l'apprentissage implicite (Sganarelle) en dialogue explicite.
-   **Mode "Pensée à voix haute"** :
    -   Sur l'interface Web, afficher le "cheminement de pensée" en temps réel (streaming) pendant que Sancho réfléchit. Voir les étapes s'allumer (Step 1: Analyzed, Step 2: Retrieving Context...) rassure sur la complexité du travail effectué (effet "Labor Illusion").

## 5. Maintenance & Scalabilité

-   **Migration Vector Store** :
    -   Si le nombre de notes explose (>10k), FAISS local en mémoire pourrait devenir limitant ou lourd au démarrage.
    -   *Suggestion* : Préparer une interface abstraite pour basculer facilement vers Qdrant ou ChromaDB (dockerisé) sans changer le code métier.
-   **Simulated User Testing** :
    -   Créer un "Virtual Johan" (un LLM scripté avec des personas et des objectifs) qui envoie des milliers d'emails de test variés pour vérifier la stabilité du raisonnement sur la durée et détecter les régressions de comportement après des mises à jour de prompt.

---

### Priorisation Suggérée

1.  **Immédiat** : Exécution Spéculative (Gain perf rapide).
2.  **Moyen terme (v1.1)** : Boucle de Feedback Explicite (Engagement utilisateur).
3.  **Long terme (v1.5)** : Consensus Multi-Modèles & Redaction Layer (Fiabilité & Sécurité).
