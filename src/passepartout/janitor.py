"""
Note Janitor Service

Responsible for maintaining the hygiene of notes:
- Validating Frontmatter
- repairing structure
- detecting broken links (future)
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from src.monitoring.logger import get_logger

logger = get_logger("passepartout.janitor")


class NoteJanitor:
    """
    The Janitor cleans up notes and ensures they adhere to the schema.
    """

    def __init__(self, notes_dir: Path):
        self.notes_dir = Path(notes_dir)
        # Regex to separate frontmatter from content
        self.frontmatter_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

    def validate_note(self, content: str) -> Tuple[bool, List[str]]:
        """
        Validate a note's structure.

        Returns:
            (is_valid, list_of_issues)
        """
        issues = []

        # Check Frontmatter
        match = self.frontmatter_pattern.match(content)
        if not match:
            issues.append("Missing or invalid frontmatter block")
            return False, issues

        fm_text = match.group(1)
        try:
            frontmatter = yaml.safe_load(fm_text)
            if not isinstance(frontmatter, dict):
                issues.append("Frontmatter is not a dictionary")
        except yaml.YAMLError as e:
            issues.append(f"Invalid YAML in frontmatter: {e}")

        return len(issues) == 0, issues

    def repair_note(self, content: str, title_fallback: str) -> str:
        """
        Attempt to repair a note's structure.

        Repairs:
        - add missing frontmatter if completely absent
        - ensure 'title' exists in frontmatter
        """
        match = self.frontmatter_pattern.match(content)

        if match:
            # Existing frontmatter
            fm_text = match.group(1)
            body = match.group(2)

            try:
                fm = yaml.safe_load(fm_text) or {}
                if not isinstance(fm, dict):
                    fm = {}  # Forced reset if corrupted

                # Ensure title
                if "title" not in fm:
                    # Try to find # H1 in body
                    h1_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
                    if h1_match:
                        fm["title"] = h1_match.group(1).strip()
                    else:
                        fm["title"] = title_fallback

                # Reconstruct
                new_fm = yaml.dump(
                    fm, allow_unicode=True, default_flow_style=False, sort_keys=False
                )
                return f"---\n{new_fm}---\n{body}"

            except yaml.YAMLError:
                # YAML is too broken, wrap entire content?
                # For safety, we return original if we can't safely parse
                logger.warning("Janitor could not parse YAML to repair it. Skipping.")
                return content
        else:
            # No frontmatter at all
            # Check if it looks like markdown
            fm = {
                "title": title_fallback,
                "created": datetime.now().isoformat(),
                "repaired_by": "NoteJanitor",
            }

            # Try to extract title from first line if H1
            lines = content.split("\n")
            if lines and lines[0].startswith("# "):
                fm["title"] = lines[0][2:].strip()

            new_fm = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
            return f"---\n{new_fm}---\n\n{content}"

    def clean_directory(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Run the janitor on the entire directory.
        """
        stats = {"scanned": 0, "issues_found": 0, "repaired": 0, "errors": 0}

        for file_path in self.notes_dir.rglob("*.md"):
            stats["scanned"] += 1
            try:
                content = file_path.read_text(encoding="utf-8")
                is_valid, issues = self.validate_note(content)

                if not is_valid:
                    stats["issues_found"] += 1
                    logger.info(f"Issues in {file_path.name}: {issues}")

                    if not dry_run:
                        # Attempt repair
                        new_content = self.repair_note(content, file_path.stem)
                        if new_content != content:
                            file_path.write_text(new_content, encoding="utf-8")
                            stats["repaired"] += 1
                            logger.info(f"Repaired {file_path.name}")
            except Exception as e:
                stats["errors"] += 1
                logger.error(f"Error processing {file_path}: {e}")

        return stats
