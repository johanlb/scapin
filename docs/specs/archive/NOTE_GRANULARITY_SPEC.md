# Note Granularity Strategy — "Project-First"

**Status**: VALIDÉ (en attente d'implémentation)
**Date**: 2026-01-15
**Auteur**: Johan + Claude

---

## Résumé exécutif

Après analyse de plusieurs emails réels, nous avons défini une nouvelle stratégie de granularité des notes qui remplace l'approche "1 entité = 1 note" par une approche **"Project-First"** plus pragmatique.

### Principes clés

1. **Project-First** : Par défaut, tout va dans la note du projet/actif concerné
2. **Trois catégories** : Projets, Domaines/Actifs, Contacts stratégiques
3. **Opérations vs Projets** : Les opérations continues vont dans l'actif, les projets temporaires ont leur note
4. **Extraction sélective** : N'extraire que si l'info sera utile
5. **Condensation** : Privilégier les entrées résumées (1-2 extractions), éviter la fragmentation

---

## 1. Problème initial

L'approche actuelle crée des notes trop atomiques (1 entité = 1 note), ce qui entraîne :

| Problème | Exemple |
|----------|---------|
| **Fragmentation** | Email Valriche → 4 notes séparées au lieu d'une |
| **Perte de contexte** | Note "Christophe Piquet" sans savoir pourquoi on le connaît |
| **Notes orphelines** | Contacts ponctuels deviennent des notes isolées |
| **Sur-extraction** | Communiqué Azuri → 7 extractions pour 1 email |
| **Extraction inutile** | Message d'anniversaire → 2 extractions sans valeur |

---

## 2. Trois catégories de notes

### 2.1 Projets (temporaires)

> Un projet a un **début et une fin**. Une fois terminé, il est clos.

**Exemples** :
- Projet Immobilier Maurice
- Gazette Arlette
- Projet Vente Nautil 6

**Structure type** :

```markdown
# Projet [Nom]

## Objectif
[But du projet]

## Contacts
- **Nom** (Rôle/Entreprise)
  Coordonnées, contexte de la relation

## Informations clés
[Faits, décisions, références importantes]

## Actions
- [ ] Tâches en cours

## Historique
- YYYY-MM-DD: Événement clé
```

### 2.2 Domaines / Actifs (permanents)

> Un domaine ou actif existe **tant qu'on le possède ou qu'il est pertinent**.

**Exemples** :
- Nautil 6 (bien immobilier)
- Résidence Azuri (copropriété)
- Infrastructure Cloud (domaine technique)
- Santé (domaine personnel)

**Structure type** :

```markdown
# [Nom de l'actif/domaine]

## Infos générales
[Caractéristiques permanentes]

## [Section opérationnelle 1]
[Ex: Location, Maintenance, Charges...]

## [Section opérationnelle 2]
[...]

## Historique
- YYYY-MM-DD: Événement notable
```

### 2.3 Contacts stratégiques (récurrents)

> Un contact stratégique apparaît dans **plusieurs contextes** et mérite sa propre note.

**Critères** :
- Mentionné dans 3+ projets/contextes différents
- Rôle clé (banquier, notaire, partenaire récurrent)
- Explicitement marqué comme stratégique dans la config

**Exemples** :
- Valerie Lincoln (banquière)
- [Notaire habituel]
- [Partenaire business récurrent]

**Structure type** :

```markdown
# [Nom de la personne]

## Rôle
[Fonction, entreprise, relation avec Johan]

## Coordonnées
- Email, téléphone, etc.

## Contextes
- [[Projet X]] — rôle dans ce projet
- [[Actif Y]] — relation avec cet actif

## Notes
[Préférences, informations utiles]
```

---

## 3. Règle "Project-First"

### 3.1 Logique d'attribution

```
Pour chaque extraction :

1. L'email concerne-t-il un PROJET ACTIF ?
   → OUI : cibler la note du projet

2. L'email concerne-t-il un ACTIF/DOMAINE ?
   → OUI : cibler la note de l'actif/domaine

3. L'entité est-elle un CONTACT STRATÉGIQUE ?
   → OUI : cibler sa note dédiée + lien dans le contexte

4. Sinon :
   → Créer une note projet si nouveau projet identifié
   → Ou ne pas extraire si pas pertinent
```

### 3.2 Exemples appliqués

| Email | Approche actuelle (❌) | Approche Project-First (✅) |
|-------|------------------------|------------------------------|
| Christophe Piquet (terrains) | 4 notes séparées | 1 note "Projet Immobilier Maurice" |
| Gazette Arlette | 4 notes (Denis, Damien, etc.) | 1 note "Gazette Arlette" |
| Fin bail Nautil 6 | 3 notes (Julien, Johan, etc.) | 1 note "Nautil 6" |
| Communiqué Azuri | 7 extractions → 1 note | 1 entrée résumée → "Résidence Azuri" |

---

## 4. Opérations vs Projets

### 4.1 Distinction clé

| Type | Caractéristique | Destination |
|------|-----------------|-------------|
| **Opération** | Continue, sans fin définie | Section dans la note actif/domaine |
| **Projet** | Temporaire, début → fin | Note projet dédiée |

### 4.2 Exemple : Nautil 6

| Aspect | Type | Destination |
|--------|------|-------------|
| Location | Opération continue | Section "Location" dans note Nautil 6 |
| Maintenance | Opération continue | Section "Maintenance" dans note Nautil 6 |
| Charges copro | Opération continue | Section "Charges" dans note Nautil 6 |
| **Vente** | **Projet temporaire** | **Note dédiée "Projet Vente Nautil 6"** |

### 4.3 Justification

- **La vente a une fin** : une fois vendu, le projet est clos
- **Les opérations sont permanentes** : tant qu'on possède le bien
- **Séparation du bruit** : le projet vente ne pollue pas la note principale

---

## 5. Extraction sélective

### 5.1 Quand extraire ?

| Critère | Extraire ? | Exemple |
|---------|------------|---------|
| Information actionnable | ✅ OUI | Deadline, engagement, demande |
| Référence à haute probabilité d'usage | ✅ OUI | Coordonnées contact clé, numéros de référence |
| Contexte utile pour futures analyses | ✅ OUI | Décision importante, fait structurant |
| Information obsolète | ❌ NON | Essai AWS expiré en 2021 |
| Email purement social | ❌ NON | "Joyeux anniversaire", "Coucou ça va ?" |
| Contenu sans valeur de référence | ❌ NON | Blagues, discussions informelles |

### 5.2 Matrice Action/Extraction

| Utilité future | Action email | Extraction |
|----------------|--------------|------------|
| **Haute** — J'aurai besoin de cette info | Archive/Queue | ✅ Extraire |
| **Basse** — Juste référence, peu probable | Archive | ❌ Non |
| **Nulle** — Aucune raison de garder | Delete | ❌ Non |

### 5.3 Exemples

| Email | Utilité | Action | Extraction |
|-------|---------|--------|------------|
| Christophe Piquet (terrains Maurice) | Haute | Queue | ✅ → Projet Immobilier |
| Julien Coette (fin de bail) | Haute | Archive | ✅ → Nautil 6 |
| Communiqué sécurité Azuri | Moyenne | Archive | ✅ condensé → Résidence Azuri |
| Yann & Denis (anniversaire) | Nulle | Archive | ❌ |
| AWS FreePBX (essai expiré 2021) | Nulle | Delete | ❌ |

---

## 6. Condensation des extractions

### 6.1 Orientation

> **Privilégier une entrée résumée** plutôt que N extractions atomiques.
> **Flexibilité** : 2-3 extractions acceptables si vraiment distinctes (types différents, cibles différentes).

### 6.2 Avant / Après

**Avant** (communiqué Azuri) — 7 extractions :
- evenement: Incident de sécurité à l'entrée
- fait: Arrestation du suspect
- fait: Équipe en congé
- decision: Renforcement gardes
- decision: Contact police
- engagement: Révision protocoles
- engagement: Coopération enquête

**Après** — 1 entrée résumée :
```markdown
### 2021-03-22 — Incident sécurité entrée
Incident viral sur réseaux sociaux. Suspect arrêté.
Mesures: renforcement gardes, contact police Rivière-du-Rempart.
Révision protocoles prévue avec conseils syndicaux.
```

### 6.3 Format recommandé

```markdown
### YYYY-MM-DD — [Titre court]
[Résumé en 2-4 lignes max]
[Actions si applicable : "À faire: ...", "Décision: ..."]
```

---

## 7. Configuration utilisateur

Fichier `_Scapin/Configuration.md` dans le PKM :

```markdown
# Configuration Scapin

## Projets actifs
Les extractions liées à ces projets vont dans leur note dédiée :
- Projet Immobilier Maurice
- Gazette Arlette
- [autres projets en cours...]

## Actifs & Domaines
Notes permanentes pour les opérations continues :
- Nautil 6
- Résidence Azuri
- Infrastructure Cloud
- [autres actifs/domaines...]

## Contacts stratégiques
Ces personnes ont des notes dédiées (apparaissent dans plusieurs contextes) :
- Valerie Lincoln (banquière)
- [autres contacts récurrents...]

## Règles personnalisées
- Emails de [domaine] → toujours vers note [X]
- [autres règles spécifiques...]
```

---

## 8. Résumé des règles

### 8.1 Attribution des notes

```
┌─────────────────────────────────────────────────────────┐
│                    EMAIL REÇU                           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  Vaut-il extraction ? │
              └───────────────────────┘
                    │           │
                   OUI         NON
                    │           │
                    ▼           ▼
         ┌──────────────┐   Archive/Delete
         │ Quel contexte │   sans extraction
         └──────────────┘
           │    │    │
           ▼    ▼    ▼
       Projet Actif Contact
           │    │    │
           ▼    ▼    ▼
    Note   Note   Note
   Projet Actif  Contact
           │    │    │
           └────┴────┘
                │
                ▼
    ┌─────────────────────┐
    │ Résumer en 1 entrée │
    │  (pas N extractions)│
    └─────────────────────┘
```

### 8.2 Checklist extraction

- [ ] L'info sera-t-elle utile plus tard ? (sinon, pas d'extraction)
- [ ] Quel est le contexte principal ? (projet > actif > contact)
- [ ] L'entrée est-elle condensée ? (1 résumé, pas N détails)
- [ ] La note cible existe-t-elle ? (sinon, la créer si pertinent)

---

## 9. Implémentation

### 9.1 Changements requis

| Composant | Modification |
|-----------|--------------|
| `pass1_blind_extraction.j2` | Nouvelles règles d'extraction sélective |
| `multi_pass_analyzer.py` | Logique de condensation |
| `context_searcher.py` | Recherche par projet/actif d'abord |
| `_Scapin/Configuration.md` | Créer le fichier de config |
| `enricher.py` | Logique d'attribution Project-First |

### 9.2 Priorité

1. **Phase 1** : Extraction sélective (ne pas extraire si inutile)
2. **Phase 2** : Condensation (résumer au lieu de détailler)
3. **Phase 3** : Attribution Project-First (cibler la bonne note)
4. **Phase 4** : Configuration utilisateur (projets/actifs/contacts)

---

## 10. Exemples de référence

### 10.1 Email projet → Note projet

**Email** : Christophe Piquet propose terrains Heritage Villas Valriche

**Extraction** :
```markdown
### 2026-01-15 — Contact Christophe Piquet (Heritage Villas Valriche)
Mise en relation via Valerie Lincoln.
Terrains disponibles: 14, 245, 264, 268 (réservés), 261 (remis en vente).
Contact: +230 5919 2487, christophe@villasvalriche.com
À faire: Planifier rendez-vous pour discuter projet.
```

**Note cible** : `Projet Immobilier Maurice`

### 10.2 Email actif → Note actif

**Email** : Julien Coette confirme non-renouvellement bail Nautil 6

**Extraction** :
```markdown
### 2021-03-08 — Départ locataires Coette
Julien & Delphine confirment départ au 14/05/2021.
Nouveau bail ailleurs démarre 15/05/2021.
À faire: Rechercher nouveaux locataires.
```

**Note cible** : `Nautil 6` (section Location)

### 10.3 Email social → Pas d'extraction

**Email** : Yann & Denis souhaitent joyeux anniversaire

**Extraction** : Aucune

**Action** : Archive

---

## Historique des décisions

| Date | Décision | Justification |
|------|----------|---------------|
| 2026-01-15 | Approche "Project-First" | Éviter fragmentation |
| 2026-01-15 | Trois catégories de notes | Couvrir tous les cas d'usage |
| 2026-01-15 | Distinction Opérations/Projets | Les projets ont une fin, pas les opérations |
| 2026-01-15 | Extraction sélective | Ne pas extraire si inutile |
| 2026-01-15 | Condensation | Un email = une entrée résumée |
