#!/usr/bin/env python3
"""
Diagnostic des collisions note_id avant migration.

Ce script identifie les fichiers .md qui ont le même nom dans différents
dossiers, ce qui cause des collisions avec le format note_id actuel (filename only).

Usage:
    python scripts/migration/note_id_diagnostic.py
    python scripts/migration/note_id_diagnostic.py --notes-dir /path/to/notes
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

# Dossiers à ignorer
IGNORED_DIRS = {".git", ".scapin_index", "_Supprimées", "__pycache__"}


def find_collisions(notes_dir: Path) -> dict[str, list[Path]]:
    """
    Trouve les fichiers avec le même nom dans différents dossiers.

    Args:
        notes_dir: Répertoire racine des notes

    Returns:
        Dict {filename_stem: [list of paths]} pour les collisions uniquement
    """
    by_stem: dict[str, list[Path]] = defaultdict(list)

    for f in notes_dir.rglob("*.md"):
        # Ignorer les dossiers système
        if any(part in IGNORED_DIRS or part.startswith(".") for part in f.parts):
            continue
        by_stem[f.stem].append(f)

    # Ne garder que les collisions (plus d'un fichier avec le même nom)
    return {k: v for k, v in by_stem.items() if len(v) > 1}


def generate_mapping(notes_dir: Path) -> dict[str, str]:
    """
    Génère le mapping old_id -> new_id pour toutes les notes.

    Le nouveau format est: chemin/relatif/sans/extension
    Exemple: "Projets/Scapin/Architecture" pour "Projets/Scapin/Architecture.md"

    Args:
        notes_dir: Répertoire racine des notes

    Returns:
        Dict {old_id: new_id} pour toutes les notes
    """
    mapping = {}

    for f in notes_dir.rglob("*.md"):
        # Ignorer les dossiers système
        if any(part in IGNORED_DIRS or part.startswith(".") for part in f.parts):
            continue

        old_id = f.stem
        new_id = str(f.relative_to(notes_dir).with_suffix(""))

        # En cas de collision, le dernier fichier trouvé écrase
        # C'est le comportement actuel qu'on veut corriger
        mapping[old_id] = new_id

    return mapping


def main():
    parser = argparse.ArgumentParser(description="Diagnostic des collisions note_id")
    parser.add_argument(
        "--notes-dir",
        type=Path,
        default=Path.home() / "Documents" / "Scapin" / "Notes",
        help="Répertoire des notes",
    )
    parser.add_argument(
        "--output-mapping",
        type=Path,
        help="Fichier JSON de sortie pour le mapping",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Afficher les détails",
    )
    args = parser.parse_args()

    notes_dir = args.notes_dir
    if not notes_dir.exists():
        print(f"ERREUR: Répertoire introuvable: {notes_dir}")
        return 1

    print(f"Analyse du répertoire: {notes_dir}\n")

    # 1. Compter les fichiers
    all_files = list(notes_dir.rglob("*.md"))
    visible_files = [
        f
        for f in all_files
        if not any(part in IGNORED_DIRS or part.startswith(".") for part in f.parts)
    ]
    print(f"Fichiers .md totaux: {len(all_files)}")
    print(f"Fichiers .md visibles: {len(visible_files)}")

    # 2. Trouver les collisions
    collisions = find_collisions(notes_dir)
    collision_count = sum(len(paths) for paths in collisions.values())

    print(f"\n{'=' * 60}")
    print(f"COLLISIONS DÉTECTÉES: {len(collisions)} noms, {collision_count} fichiers")
    print(f"{'=' * 60}\n")

    if collisions:
        for stem, paths in sorted(collisions.items()):
            print(f"📁 {stem}.md ({len(paths)} fichiers)")
            for p in paths:
                rel_path = p.relative_to(notes_dir)
                print(f"   └── {rel_path}")
            print()

    # 3. Générer le mapping
    mapping = generate_mapping(notes_dir)

    # Statistiques
    unique_new_ids = set(mapping.values())
    print(f"{'=' * 60}")
    print("STATISTIQUES")
    print(f"{'=' * 60}")
    print(f"Notes avec ancien format (filename): {len(mapping)}")
    print(f"Notes avec nouveau format (path): {len(unique_new_ids)}")
    print(f"Notes perdues par collision: {len(mapping) - len(unique_new_ids)}")

    # Impact sur l'index
    expected_after = len(visible_files)
    current_indexed = len(unique_new_ids)  # Simule le comportement actuel
    print(f"\nIndex actuel (estimé): {current_indexed} notes")
    print(f"Index après migration: {expected_after} notes")
    print(f"Gain: +{expected_after - current_indexed} notes")

    # 4. Sauvegarder le mapping si demandé
    if args.output_mapping:
        # Créer le mapping complet old_id -> new_id
        full_mapping = {}
        for f in visible_files:
            old_id = f.stem
            new_id = str(f.relative_to(notes_dir).with_suffix(""))
            if old_id not in full_mapping:
                full_mapping[old_id] = []
            full_mapping[old_id].append(new_id)

        with open(args.output_mapping, "w") as fp:
            json.dump(full_mapping, fp, indent=2, ensure_ascii=False)
        print(f"\nMapping sauvegardé: {args.output_mapping}")

    return 0


if __name__ == "__main__":
    exit(main())
