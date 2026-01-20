# Session Context: Mise à jour Documentation Utilisateur

**Branche** : `docs/user-guide-update`
**Objectif** : Mettre à jour les guides utilisateur existants avec les fonctionnalités v2.5

---

## Contexte du Projet

Scapin est un gardien cognitif personnel qui analyse les emails via IA multi-pass et les organise avec une mémoire contextuelle.

**Documentation existante** : `docs/user-guide/`

| Fichier | Contenu | Priorité MAJ |
|---------|---------|--------------|
| `README.md` | Index général | Basse |
| `01-demarrage.md` | Installation, premiers pas | Basse |
| `02-briefing.md` | Page Briefing | Basse |
| `03-flux.md` | Page Péripéties (flux emails) | **HAUTE** |
| `04-notes.md` | Système de notes | Moyenne |
| `05-journal.md` | Journal quotidien | Basse |
| `06-architecture.md` | Architecture technique | Basse |
| `07-configuration.md` | Configuration | Basse |

---

## Nouveautés v2.5 à Documenter

### 1. Vue Élément Unique Enrichie (Page Péripéties)

**Fichier** : `03-flux.md`

La vue d'un élément à traiter affiche maintenant par défaut (sans avoir à ouvrir les détails) :

#### Timestamps enrichis
- 📨 **Reçu** : Date de réception de l'email
- 🧠 **Analysé** : Date d'analyse par Scapin
- (Les badges de complexité sont à côté)

#### Avatar expéditeur
- Avatar circulaire avec initiales (ex: "JC" pour Julien Coette)
- Affichage du nom ET de l'adresse email complète

#### Badges de complexité (visibles par défaut)
Maintenant affichés directement dans la vue élément unique, pas seulement dans la liste :
- ⚡ = Analyse rapide (1 pass Haiku)
- 🔍 = Contexte personnel utilisé
- 🧠 = Analyse complexe (3+ passes)
- 🏆 = Opus utilisé

#### Section "Influence du Contexte" (visible par défaut)
Auparavant cachée dans "Détails", maintenant visible directement :
- **Explication** : Comment le contexte a influencé l'analyse
- **Notes utilisées** : Badges des notes PKM consultées
- **Confirmations** (✓) : Infos confirmées par le contexte
- **Contradictions** (⚠) : Incohérences détectées
- **Manquant** (❓) : Infos recherchées mais non trouvées

#### Section "Contexte Récupéré" (collapsible)
Nouvelle section visible par défaut (fermée mais accessible) :
- **Entités recherchées** : Liste des entités identifiées
- **Notes trouvées** : Avec pourcentage de pertinence et lien
- **Événements calendrier** : Réunions liées
- **Tâches OmniFocus** : Actions associées
- **Sources consultées** : PKM, Calendrier, OmniFocus...

#### Section Pièces Jointes
Affichage des pièces jointes avec le composant FileAttachment (comme dans l'historique).

---

## Instructions pour la Mise à Jour

### Ce qu'il faut faire

1. **Mettre à jour `03-flux.md`** :
   - Ajouter une section "Vue Élément Unique (v2.5)" décrivant la nouvelle interface
   - Mettre à jour les captures d'écran ou descriptions textuelles
   - Expliquer la nouvelle organisation de l'information (contexte visible par défaut)

2. **Vérifier la cohérence** :
   - S'assurer que les références aux versions sont correctes (v2.3, v2.4, v2.5)
   - Vérifier que le vocabulaire est cohérent (Péripéties, pas Flux)

3. **Mettre à jour `README.md`** si nécessaire :
   - Ajouter mention de la version 2.5

### Ce qu'il ne faut PAS faire

- Ne pas réécrire entièrement les fichiers
- Ne pas supprimer les sections existantes sur v2.3 et v2.4 (elles sont valides)
- Ne pas ajouter de nouvelles pages de documentation

### Style d'écriture

- Français, ton professionnel mais accessible
- Utiliser des tableaux pour les listes d'options
- Inclure des exemples concrets
- Utiliser des emojis pour les icônes UI (📨, 🧠, etc.)

---

## Fichiers de Référence

Pour comprendre les nouvelles fonctionnalités, consulter :

- `web/src/routes/peripeties/+page.svelte` : Code de la page (sections SECTION 2, 4.5, 4.6, 10.5)
- `web/src/routes/peripeties/[id]/+page.svelte` : Page historique (modèle de référence)

---

## Commandes Utiles

```bash
# Vérifier la branche
git branch

# Voir les fichiers de documentation
ls -la docs/user-guide/

# Lire un fichier
cat docs/user-guide/03-flux.md

# Après modifications, committer
git add docs/user-guide/
git commit -m "docs: update user guide for v2.5 features"
```

---

## Critères de Succès

- [ ] `03-flux.md` contient une section décrivant la vue élément unique v2.5
- [ ] Les timestamps, avatar, badges sont documentés
- [ ] La section Context Influence est documentée
- [ ] La section Retrieved Context est documentée
- [ ] La section pièces jointes est mentionnée
- [ ] Le README mentionne la version 2.5

---

## Pour Démarrer la Session

```bash
cd /Users/johan/Developer/scapin
git checkout docs/user-guide-update
# Lire ce fichier puis commencer par 03-flux.md
```
