# 4. Notes

Les **Notes** sont le cœur de votre base de connaissances. Scapin utilise vos notes pour enrichir l'analyse des emails et vous aide à les maintenir à jour.

---

## Structure

### Organisation : Stratégie "Project-First"

Scapin privilégie une organisation **centralisée** pour éviter la fragmentation. Au lieu de dizaines de petites notes atomiques, l'information est regroupée dans des notes "piliers" :

```
notes/
├── projets/           # Notes centrales pour chaque projet actif
│   ├── Projet_Alpha.md
│   └── Projet_Beta.md
├── domaines/          # Actifs, finances, santé, administration
│   ├── Maison.md      # Tout ce qui concerne le domicile
│   └── Fiscalité.md
├── relations/         # Fiches détaillées des contacts clés
│   ├── Jean_Dupont.md
│   └── Marie_Martin.md
└── journal/           # Entrées quotidiennes fusionnées
    └── 2026-01.md     # Journal mensuel
```

### Types de Notes

| Type | Usage | Icône |
|------|-------|-------|
| **Projet** | Initiatives, dossiers, chantiers | 📁 |
| **Personne** | Contacts clés, partenaires | 👤 |
| **Actif** | Biens, investissements, lieux | 🏠 |
| **Domaine** | Sujets transverses (Santé, Finance) | 🛡️ |
| **Réunion** | Comptes-rendus (souvent liés à un Projet) | 📅 |

---

## Interface

L'interface Notes est organisée en **3 colonnes** style Apple Notes :

| Colonne | Contenu | Largeur |
|---------|---------|---------|
| **1** | Arbre de dossiers | 224px |
| **2** | Liste des notes + Recherche | 288px |
| **3** | Contenu de la note | Flexible |

### Arbre de Dossiers (Colonne 1)

- Navigation hiérarchique avec expansion/collapse
- Dossiers virtuels : "Toutes les notes" et "Supprimées récemment"
- Compteur de notes par dossier
- Créer dossiers avec clic droit
- Glisser-déposer pour organiser

### Notes Épinglées

Vos notes favorites en accès rapide.

### Recherche API (Colonne 2)

La barre de recherche en haut de la colonne 2 permet une recherche puissante dans toutes vos notes.

**Raccourci clavier** : `Cmd+K` (ou `Ctrl+K`)

**Fonctionnalités** :
- Recherche hybride : full-text + sémantique
- Debounce automatique (300ms)
- Score de pertinence affiché (badge coloré)
- Extraits avec highlights des termes trouvés
- Chemin du dossier affiché pour chaque résultat

**Actions** :
- `Escape` ou clic sur ✕ : Effacer la recherche
- Clic sur un résultat : Ouvre la note

### Édition du Titre (Colonne 3)

**Double-clic** sur le titre d'une note pour l'éditer directement.

| Action | Résultat |
|--------|----------|
| Double-clic sur titre | Passe en mode édition |
| `Enter` | Sauvegarde le titre |
| `Escape` | Annule les modifications |
| Clic ailleurs | Sauvegarde le titre |
| ✓ | Sauvegarde |
| ✕ | Annule |

---

## Éditeur Markdown

### Modes

| Mode | Description |
|------|-------------|
| **Écrire** | Édition pure Markdown |
| **Aperçu** | Rendu HTML |
| **Split** | Édition + aperçu côte à côte |

### Barre d'Outils

| Bouton | Raccourci | Action |
|--------|-----------|--------|
| **B** | `Cmd+B` | Gras |
| *I* | `Cmd+I` | Italique |
| `</>` | `Cmd+E` | Code |
| 🔗 | `Cmd+K` | Lien |
| [[]] | `Cmd+W` | Wikilink |

### Wikilinks

Créez des liens entre notes :

```markdown
Voir [[Jean Dupont]] pour le contexte du [[Projet Alpha]].
```

Les wikilinks sont cliquables dans l'aperçu.

### Auto-Save

- Sauvegarde automatique après 1 seconde d'inactivité
- Indicateur "Enregistré" / "Enregistrement..."

---

## Révision Espacée (SM-2)

Scapin utilise l'algorithme **SuperMemo 2** pour vous aider à maintenir vos notes à jour.

### Principe

1. Nouvelle note → Révision dans 2h
2. Bonne révision → Intervalle augmente
3. Mauvaise révision → Retour au début

### Intervalles

| Qualité | Intervalle suivant |
|---------|-------------------|
| 5 (Parfait) | × 2.5 |
| 4 (Hésitation) | × 2.0 |
| 3 (Difficulté) | × 1.5 |
| 2 (Oubli partiel) | 1 jour |
| 1 (Oubli total) | 10 min |
| 0 (Blackout) | 1 min |

### Page Révision

Accès : `/notes/review` ou widget Dashboard

1. Note affichée
2. Réfléchir (sans voir le contenu)
3. Révéler le contenu
4. Noter la qualité (1-6)
5. Note suivante

### Raccourcis Révision

| Touche | Action |
|--------|--------|
| `1-6` | Noter la qualité |
| `←/→` | Naviguer |
| `s` | Reporter (snooze) |
| `Escape` | Quitter |

---

## Historique (Git)

Chaque note est versionnée avec Git.

### Voir l'Historique

1. Ouvrir une note
2. Cliquer 🕐 (Historique)
3. Liste des versions

### Comparer

1. Sélectionner deux versions
2. Voir le diff (ajouts/suppressions)

### Restaurer

1. Sélectionner une version
2. Cliquer "Restaurer"
3. Confirmer

---

## Synchronisation Apple Notes

### Import

1. Aller dans Notes
2. Cliquer "Sync Apple Notes"
3. Attendre la synchronisation

### Mapping

- Dossier Apple Notes → Dossier Scapin
- Contenu HTML → Markdown

### Bidirectionnel

- Modifications dans Scapin → Apple Notes
- Modifications dans Apple Notes → Scapin
- Conflits résolus par date de modification

---

## Revue Hygiène

Le bouton **🧹 Revue Hygiène** analyse la qualité de la note sélectionnée et suggère des améliorations.

### Lancer une Revue

1. Sélectionner une note
2. Cliquer sur le bouton 🧹 dans la barre d'outils

### États du Bouton

| État | Apparence | Signification |
|------|-----------|---------------|
| **Idle** | 🧹 | Prêt pour la revue |
| **Loading** | ⏳ | Analyse en cours |
| **Issues** | 🧹 + Badge rouge | Problèmes détectés |
| **Clean** | ✨ | Note impeccable |

### Types de Problèmes Détectés

| Type | Description |
|------|-------------|
| **Lien cassé** | Wikilink vers note inexistante |
| **Orpheline** | Note sans liens entrants |
| **Obsolète** | Contenu potentiellement périmé |
| **Incomplet** | Section manquante ou vide |
| **Doublon** | Information dupliquée ailleurs |
| **Format** | Problème de formatage Markdown |

### Panneau de Résultats

Le panneau affiche chaque problème avec :
- **Icône de sévérité** : 🔴 Erreur, 🟡 Avertissement, ℹ️ Info
- **Description** du problème
- **Suggestion** de correction (optionnel)
- **Confiance** de la détection (0-100%)

### Actions

- Cliquer sur un problème pour voir les détails
- Bouton "Corriger" pour appliquer une suggestion automatique
- Bouton "Ignorer" pour masquer un problème

---

## Média (Images, Audio, Vidéo, PDF)

Les notes synchronisées depuis Apple Notes peuvent contenir des médias embarqués.

### Types Supportés

| Type | Extensions | Affichage |
|------|------------|-----------|
| **Images** | jpg, png, gif, webp, heic | Inline avec lazy loading |
| **Audio** | m4a, mp3, wav | Lecteur audio natif |
| **Vidéo** | mp4, mov | Lecteur vidéo natif |
| **PDF** | pdf | Iframe intégrée |

### Syntaxe Apple Media

Les médias Apple Notes utilisent le protocole `apple-media://` :

```markdown
![Description](apple-media://attachment-uuid)
```

Scapin convertit automatiquement ces URLs vers `/api/media/{uuid}` pour l'affichage.

### Cache et Performance

- **Lazy loading** : Les images ne sont chargées que lorsqu'elles sont visibles
- **Cache 24h** : Les médias sont mis en cache côté navigateur
- **Optimisation** : Les grandes images sont servies avec des headers de cache appropriés

---

## Enrichissement Automatique

### Sources

Scapin enrichit vos notes depuis :
- Emails traités
- Messages Teams
- Événements calendrier
- Web (recherche)

### Processus

1. Scapin détecte une entité (ex: personne)
2. Cherche la note existante
3. Propose un enrichissement
4. Vous validez ou modifiez
5. Note mise à jour

### Auto-Apply

Si confiance > 90% :
- Enrichissement appliqué automatiquement
- Badge "Auto" dans l'historique
- Révisable à tout moment

---

## Conseils

1. **Utilisez les wikilinks** — Créez un réseau de connaissances
2. **Révisez 5 min/jour** — Gardez vos notes fraîches
3. **Typez vos notes** — Aide Scapin à mieux les utiliser
4. **Épinglez l'essentiel** — Accès rapide aux notes clés
