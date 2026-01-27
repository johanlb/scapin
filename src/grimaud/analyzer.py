"""
Grimaud Analyzer — Detection de problemes dans les notes PKM.

Detecte les problemes locaux (sans IA) et utilise l'IA pour des analyses
approfondies et suggestions d'actions.
"""

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from src.grimaud.models import GrimaudAction, GrimaudActionType
from src.monitoring.logger import get_logger

if TYPE_CHECKING:
    from src.passepartout.note_manager import NoteManager

logger = get_logger("grimaud.analyzer")

# Regex pour extraire les wikilinks: [[target]] ou [[target|label]]
WIKILINK_PATTERN = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

# Regex pour les headers markdown (## Header)
HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


class ProblemType(str, Enum):
    """Types de problemes detectables dans une note."""

    EMPTY_SECTION = "empty_section"
    BROKEN_LINK = "broken_link"
    MISSING_FRONTMATTER = "missing_frontmatter"
    SIMILAR_NOTE = "similar_note"
    OUTDATED = "outdated"
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"


class Severity(str, Enum):
    """Severite d'un probleme."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class DetectedProblem:
    """Probleme detecte dans une note."""

    problem_type: ProblemType
    severity: Severity
    details: str


class GrimaudAnalyzer:
    """
    Analyseur de notes PKM pour Grimaud.

    Detecte les problemes locaux (sections vides, liens casses, etc.)
    et utilise l'IA pour des analyses plus approfondies.
    """

    # Seuil minimum de mots pour une note
    MIN_WORDS = 50

    def __init__(self, note_manager: "NoteManager"):
        """
        Initialise l'analyseur.

        Args:
            note_manager: Gestionnaire de notes pour validation des liens
        """
        self._note_manager = note_manager

    def detect_local_problems(
        self, content: str, frontmatter: dict
    ) -> list[DetectedProblem]:
        """
        Detecte les problemes locaux sans appel IA.

        Args:
            content: Contenu markdown de la note
            frontmatter: Dictionnaire du frontmatter

        Returns:
            Liste des problemes detectes
        """
        problems: list[DetectedProblem] = []

        # 1. Verifier le frontmatter
        if not frontmatter.get("title"):
            problems.append(
                DetectedProblem(
                    problem_type=ProblemType.MISSING_FRONTMATTER,
                    severity=Severity.MEDIUM,
                    details="Frontmatter manquant ou sans titre",
                )
            )

        # 2. Detecter les sections vides
        problems.extend(self._detect_empty_sections(content))

        # 3. Detecter les wikilinks casses
        problems.extend(self._detect_broken_links(content))

        # 4. Detecter les notes trop courtes
        word_count = self._count_words(content)
        if word_count < self.MIN_WORDS:
            problems.append(
                DetectedProblem(
                    problem_type=ProblemType.TOO_SHORT,
                    severity=Severity.LOW,
                    details=f"Note trop courte: {word_count} mots (minimum: {self.MIN_WORDS})",
                )
            )

        logger.debug(
            "Problemes locaux detectes",
            extra={"count": len(problems), "types": [p.problem_type.value for p in problems]},
        )

        return problems

    def _detect_empty_sections(self, content: str) -> list[DetectedProblem]:
        """Detecte les sections markdown vides (H2+ seulement, pas H1)."""
        problems = []

        # Trouver tous les headers
        headers = list(HEADER_PATTERN.finditer(content))

        for i, match in enumerate(headers):
            header_level = len(match.group(1))  # Nombre de #
            header_text = match.group(2).strip()
            header_end = match.end()

            # Ignorer les H1 (titres de document)
            if header_level == 1:
                continue

            # Trouver le prochain header ou la fin du document
            next_header_start = (
                headers[i + 1].start() if i + 1 < len(headers) else len(content)
            )

            # Extraire le contenu entre ce header et le suivant
            section_content = content[header_end:next_header_start].strip()

            # Section vide si pas de contenu significatif
            if not section_content or len(section_content) < 3:
                problems.append(
                    DetectedProblem(
                        problem_type=ProblemType.EMPTY_SECTION,
                        severity=Severity.MEDIUM,
                        details=f"Section vide: {header_text}",
                    )
                )

        return problems

    def _detect_broken_links(self, content: str) -> list[DetectedProblem]:
        """Detecte les wikilinks vers des notes inexistantes."""
        problems = []

        # Extraire tous les wikilinks
        wikilinks = WIKILINK_PATTERN.findall(content)

        for target in wikilinks:
            # Verifier si la note cible existe
            try:
                note = self._note_manager.find_note_by_alias(target)
                if note is None:
                    problems.append(
                        DetectedProblem(
                            problem_type=ProblemType.BROKEN_LINK,
                            severity=Severity.MEDIUM,
                            details=f"Lien casse: [[{target}]]",
                        )
                    )
            except Exception as e:
                logger.warning(f"Erreur verification lien {target}: {e}")

        return problems

    def _count_words(self, content: str) -> int:
        """Compte le nombre de mots dans le contenu."""
        # Retirer les liens markdown, headers, etc.
        text = re.sub(r"\[.*?\]\(.*?\)", "", content)  # [text](url)
        text = re.sub(r"\[\[.*?\]\]", "", text)  # [[wikilink]]
        text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)  # headers
        text = re.sub(r"[#*_`~]", "", text)  # markdown formatting

        return len(text.split())

    def detect_similar_notes(
        self, note_id: str, threshold: float = 0.85
    ) -> list[tuple[str, float]]:
        """
        Detecte les notes similaires via recherche vectorielle.

        Args:
            note_id: ID de la note a comparer
            threshold: Seuil de similarite minimum (0.0-1.0)

        Returns:
            Liste de tuples (note_id, score) des notes similaires
        """
        try:
            # Recuperer la note pour avoir son contenu
            note = self._note_manager.get_note(note_id)
            if not note:
                logger.warning(f"Note non trouvee pour similarite: {note_id}")
                return []

            # Rechercher les notes similaires
            results = self._note_manager.search_notes(
                query=note.content,
                top_k=10,
                return_scores=True,
            )

            # Filtrer par seuil et exclure la note elle-meme
            similar = []
            for found_note, score in results:
                if found_note.note_id != note_id and score >= threshold:
                    similar.append((found_note.note_id, score))

            logger.debug(
                "Notes similaires trouvees",
                extra={"note_id": note_id, "count": len(similar), "threshold": threshold},
            )

            return similar

        except Exception as e:
            logger.error(f"Erreur detection notes similaires: {e}")
            return []

    async def analyze_with_ai(
        self,
        note_id: str,
        note_title: str,
        content: str,
        problems: list[DetectedProblem],
    ) -> list[GrimaudAction]:
        """
        Analyse approfondie avec IA et suggestions d'actions.

        Args:
            note_id: ID de la note
            note_title: Titre de la note
            content: Contenu de la note
            problems: Problemes deja detectes localement

        Returns:
            Liste d'actions suggerees par l'IA
        """
        from src.sancho.cost_calculator import AIModel
        from src.sancho.router import get_ai_router

        try:
            router = get_ai_router()

            # Construire le prompt
            problems_text = "\n".join(
                f"- {p.problem_type.value}: {p.details}" for p in problems
            ) if problems else "Aucun probleme detecte localement."

            prompt = f"""Analyse cette note PKM et suggere des actions d'amelioration.

Titre: {note_title}
Problemes detectes:
{problems_text}

Contenu:
{content[:2000]}

Reponds en JSON avec la structure suivante:
{{
    "actions": [
        {{
            "action_type": "enrichissement|liaison|restructuration|metadonnees|archivage",
            "confidence": 0.0-1.0,
            "reasoning": "Explication courte"
        }}
    ]
}}

Types d'actions disponibles:
- enrichissement: Completer des sections vides ou ajouter du contenu
- liaison: Creer des liens vers d'autres notes
- restructuration: Reorganiser la structure de la note
- metadonnees: Corriger ou completer le frontmatter
- archivage: Marquer la note comme obsolete

Ne suggere que des actions pertinentes. Si la note est bien, retourne une liste vide.
"""

            # Appeler l'IA
            response, _usage = await router.analyze_with_prompt_async(
                prompt=prompt,
                model=AIModel.CLAUDE_SONNET,
                max_tokens=1024,
            )

            # Parser la reponse JSON
            actions = self._parse_ai_response(response, note_id, note_title)

            logger.info(
                "Analyse IA terminee",
                extra={"note_id": note_id, "actions_count": len(actions)},
            )

            return actions

        except Exception as e:
            logger.error(f"Erreur analyse IA: {e}")
            return []

    def _parse_ai_response(
        self, response: str, note_id: str, note_title: str
    ) -> list[GrimaudAction]:
        """Parse la reponse JSON de l'IA en actions Grimaud."""
        try:
            # Extraire le JSON de la reponse
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                logger.warning("Pas de JSON dans la reponse IA")
                return []

            json_str = response[json_start:json_end]
            data = json.loads(json_str)

            actions = []
            for action_data in data.get("actions", []):
                action_type_str = action_data.get("action_type", "").lower()

                # Mapper vers GrimaudActionType
                action_type_map = {
                    "enrichissement": GrimaudActionType.ENRICHISSEMENT,
                    "liaison": GrimaudActionType.LIAISON,
                    "restructuration": GrimaudActionType.RESTRUCTURATION,
                    "metadonnees": GrimaudActionType.METADONNEES,
                    "archivage": GrimaudActionType.ARCHIVAGE,
                    "fusion": GrimaudActionType.FUSION,
                }

                action_type = action_type_map.get(action_type_str)
                if not action_type:
                    logger.warning(f"Type d'action inconnu: {action_type_str}")
                    continue

                action = GrimaudAction(
                    action_type=action_type,
                    note_id=note_id,
                    note_title=note_title,
                    confidence=float(action_data.get("confidence", 0.0)),
                    reasoning=action_data.get("reasoning", ""),
                )
                actions.append(action)

            return actions

        except json.JSONDecodeError as e:
            logger.warning(f"Erreur parsing JSON IA: {e}")
            return []
        except Exception as e:
            logger.error(f"Erreur parsing reponse IA: {e}")
            return []
