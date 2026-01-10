# Bug #54 : Stratégie de nommage des dossiers email

**Date** : 10 janvier 2026
**Priorité** : MOYENNE
**Statut** : Analyse et propositions

---

## Problème identifié

L'IA propose parfois des dossiers :
1. En anglais au lieu du français
2. Trop spécifiques (risque de créer des centaines de dossiers)
3. Avec des noms peu explicites
4. Sans cohérence avec la structure existante

**Objectif** : Limiter à 10-30 dossiers thématiques clairs en français.

---

## Analyse de l'existant

### Template actuel (`templates/ai/email_analysis.j2`)

Le template injecte déjà les dossiers existants :
```jinja2
{% if existing_folders and existing_folders|length > 0 %}
**DOSSIERS EXISTANTS (UTILISER EN PRIORITÉ) :**
{% for folder in existing_folders %}
- {{ folder }}
{% endfor %}
```

**Problèmes identifiés** :
1. Pas de liste de dossiers "canoniques" suggérée
2. Pas de règles claires pour la création de nouveaux dossiers
3. L'IA peut inventer des chemins arbitraires

---

## Propositions d'amélioration

### Option A : Liste de dossiers canoniques (Recommandée)

Définir une liste de 15-20 dossiers thématiques en français que l'IA doit utiliser en priorité :

```yaml
# config/folder_taxonomy.yaml
archive_folders:
  # Professionnel
  - name: "Travail/Projets"
    description: "Emails liés aux projets en cours ou passés"
    keywords: ["projet", "milestone", "livrable", "planning"]

  - name: "Travail/Administration"
    description: "RH, contrats, fiches de paie, notes de frais"
    keywords: ["contrat", "rh", "paie", "congés"]

  - name: "Travail/Clients"
    description: "Communications avec les clients"
    keywords: ["client", "devis", "facture"]

  - name: "Travail/Équipe"
    description: "Communications internes, équipe"
    keywords: ["équipe", "réunion", "standup"]

  # Personnel
  - name: "Personnel/Famille"
    description: "Échanges avec la famille"
    keywords: ["famille"]

  - name: "Personnel/Amis"
    description: "Échanges avec les amis"
    keywords: ["amis"]

  # Finance
  - name: "Finance/Banque"
    description: "Relevés, notifications bancaires"
    keywords: ["banque", "compte", "virement"]

  - name: "Finance/Factures"
    description: "Factures, reçus d'achat"
    keywords: ["facture", "reçu", "paiement"]

  - name: "Finance/Impôts"
    description: "Documents fiscaux"
    keywords: ["impôt", "déclaration", "fisc"]

  - name: "Finance/Assurances"
    description: "Contrats et communications assurances"
    keywords: ["assurance", "sinistre", "cotisation"]

  # Services
  - name: "Services/Abonnements"
    description: "Services numériques, SaaS, streaming"
    keywords: ["abonnement", "renouvellement", "subscription"]

  - name: "Services/Médical"
    description: "Santé, médecin, mutuelle"
    keywords: ["médecin", "ordonnance", "mutuelle", "santé"]

  - name: "Services/Administratif"
    description: "Administrations, impôts, CAF"
    keywords: ["administration", "caf", "préfecture"]

  # Achats
  - name: "Achats/Commandes"
    description: "Confirmations de commandes"
    keywords: ["commande", "livraison", "expédition"]

  - name: "Achats/Voyages"
    description: "Billets, réservations, hôtels"
    keywords: ["billet", "réservation", "vol", "hôtel"]

  # Autres
  - name: "Newsletters"
    description: "Newsletters gardées pour référence"
    keywords: ["newsletter", "digest"]

  - name: "Notifications"
    description: "Alertes et notifications gardées"
    keywords: ["notification", "alerte"]

  - name: "Divers"
    description: "Emails ne rentrant dans aucune autre catégorie"
    keywords: []
```

**Avantages** :
- Structure cohérente et prévisible
- Noms clairs en français
- Maximum 20 catégories principales
- Facile à étendre par l'utilisateur

### Option B : Règles de création de dossiers

Ajouter des règles strictes dans le prompt :

```
**RÈGLES DE CRÉATION DE DOSSIERS :**

1. **LANGUE** : Tous les noms de dossiers DOIVENT être en FRANÇAIS
   - ❌ "Work/Projects" → ✅ "Travail/Projets"
   - ❌ "Finance/Invoices" → ✅ "Finance/Factures"

2. **STRUCTURE** : Maximum 2 niveaux de profondeur
   - ✅ "Travail/Projets"
   - ✅ "Finance/Factures"
   - ❌ "Travail/Projets/Client-X/2025/Q1"

3. **GÉNÉRALISATION** : Préférer les catégories larges
   - ❌ "Travail/Projet-Alpha" → ✅ "Travail/Projets"
   - ❌ "Finance/Facture-Amazon" → ✅ "Finance/Factures"

4. **COHÉRENCE** : Réutiliser les dossiers existants
   - Si "Travail/Projets" existe, NE PAS créer "Travail/Projects"

5. **LIMITE** : Maximum 30 dossiers distincts dans l'archive
```

### Option C : Validation côté backend

Ajouter une validation qui :
1. Vérifie que le dossier proposé est en français
2. Suggère un dossier existant similaire si disponible
3. Refuse les chemins trop profonds (> 2 niveaux)
4. Alerte si trop de dossiers distincts (> 30)

---

## Plan d'implémentation recommandé

### Phase 1 : Mise à jour du prompt (Quick Win)

**Fichier** : `templates/ai/email_analysis.j2`

Ajouter après les dossiers existants :

```jinja2
**DOSSIERS CANONIQUES (À UTILISER EN PRIORITÉ) :**
- Travail/Projets
- Travail/Administration
- Travail/Clients
- Travail/Équipe
- Personnel/Famille
- Personnel/Amis
- Finance/Banque
- Finance/Factures
- Finance/Impôts
- Finance/Assurances
- Services/Abonnements
- Services/Médical
- Services/Administratif
- Achats/Commandes
- Achats/Voyages
- Newsletters
- Notifications
- Divers

**RÈGLES DE NOMMAGE :**
1. TOUJOURS utiliser un dossier canonique si pertinent
2. Noms en FRANÇAIS uniquement
3. Maximum 2 niveaux (Catégorie/Sous-catégorie)
4. Privilégier les catégories larges aux dossiers spécifiques
```

### Phase 2 : Configuration externe

**Fichier** : `config/folder_taxonomy.yaml`

Permettre à l'utilisateur de personnaliser sa taxonomie de dossiers.

### Phase 3 : Validation backend

Ajouter une validation dans `QueueService` qui :
- Normalise les noms de dossiers (accents, casse)
- Suggère des alternatives si le dossier n'existe pas
- Avertit l'utilisateur avant de créer un nouveau dossier

---

## Estimation d'effort

| Phase | Action | Effort |
|-------|--------|--------|
| 1 | Mise à jour du prompt | 1h |
| 2 | Configuration externe | 2h |
| 3 | Validation backend | 4h |

---

## Métriques de succès

| Métrique | Actuel | Objectif |
|----------|--------|----------|
| Nombre de dossiers distincts | ? | < 30 |
| % dossiers en français | ? | 100% |
| % réutilisation dossiers existants | ? | > 80% |

---

*Document créé le 10 janvier 2026*
