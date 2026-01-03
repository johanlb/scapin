"""
Sancho - Reasoning Engine

The cognitive heart of Scapin's assistant intelligence.
Performs iterative multi-pass reasoning to achieve high-confidence decisions.

Named after Sancho Panza (Don Quixote) - the wise and pragmatic companion
who provides grounded reasoning and sound judgment.

Architecture:
- Pass 1: Initial quick analysis (~60-70% confidence) - 2-3s
- Pass 2: Context enrichment with Scapin (~75-85% confidence) - 3-5s
- Pass 3: Deep multi-step reasoning (~85-92% confidence) - 2-4s
- Pass 4: Cross-provider validation (~90-96% confidence) - 3-5s
- Pass 5: User clarification if needed (~95-99% confidence) - async

Total time: 10-20 seconds for thorough, context-aware decisions
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from src.core.events import PerceivedEvent
from src.core.memory.working_memory import (
    Hypothesis,
    ReasoningPass,
    WorkingMemory,
)
from src.core.schemas import EmailAction, EmailAnalysis, EmailCategory
from src.sancho.router import AIModel, AIRouter
from src.sancho.templates import TemplateManager, get_template_manager

logger = logging.getLogger(__name__)


# ============================================================================
# RESULT DATACLASS
# ============================================================================


@dataclass
class ReasoningResult:
    """
    Result of Sancho's reasoning process

    Contains:
    - Working memory (full cognitive state)
    - Final analysis/decision
    - Reasoning trace (all passes)
    - Confidence and performance metrics
    """
    working_memory: WorkingMemory
    final_analysis: Optional[EmailAnalysis]  # Email-specific for now
    reasoning_trace: list[ReasoningPass]
    confidence: float
    passes_executed: int
    total_duration_seconds: float
    converged: bool  # True if reached confidence threshold

    # Additional insights
    key_factors: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    questions_for_user: list[dict[str, Any]] = field(default_factory=list)


# ============================================================================
# REASONING ENGINE
# ============================================================================


class ReasoningEngine:
    """
    Sancho's Iterative Reasoning Engine

    Performs multi-pass reasoning with confidence convergence.
    Stops when confidence >= threshold OR max passes reached.

    Design Philosophy:
    - Quality over speed (10-20s is acceptable for good decisions)
    - Iterative refinement (each pass builds on previous)
    - Context-aware (leverages Scapin knowledge base)
    - Explainable (full reasoning trace preserved)
    - Adaptive (stops early if confident, continues if uncertain)

    Example:
        >>> engine = ReasoningEngine(ai_router, template_manager)
        >>> result = engine.reason(perceived_event)
        >>> if result.converged:
        ...     execute_action(result.final_analysis.action)
    """

    def __init__(
        self,
        ai_router: AIRouter,
        template_manager: Optional[TemplateManager] = None,
        max_iterations: int = 5,
        confidence_threshold: float = 0.95,
        enable_context: bool = False,  # Phase 0.5 Week 3 feature
        enable_validation: bool = False,  # Multi-provider validation
    ):
        """
        Initialize reasoning engine

        Args:
            ai_router: AI router for LLM calls
            template_manager: Template manager (optional, uses singleton if None)
            max_iterations: Maximum reasoning passes (default 5)
            confidence_threshold: Target confidence 0.0-1.0 (default 0.95 = 95%)
            enable_context: Enable Pass 2 context retrieval (requires Passepartout)
            enable_validation: Enable Pass 4 multi-provider validation
        """
        self.ai_router = ai_router
        self.template_manager = template_manager or get_template_manager()
        self.max_iterations = max_iterations
        self.confidence_threshold = confidence_threshold
        self.enable_context = enable_context
        self.enable_validation = enable_validation

        logger.info(
            "Sancho reasoning engine initialized",
            extra={
                "max_iterations": max_iterations,
                "confidence_threshold": confidence_threshold,
                "enable_context": enable_context,
                "enable_validation": enable_validation,
            }
        )

    def reason(self, event: PerceivedEvent) -> ReasoningResult:
        """
        Main reasoning loop - iteratively refine understanding until confident

        Args:
            event: The perceived event to reason about

        Returns:
            ReasoningResult with final analysis and full trace

        Example:
            >>> event = EmailNormalizer.normalize(metadata, content)
            >>> result = engine.reason(event)
            >>> print(f"Confidence: {result.confidence:.1%} in {result.passes_executed} passes")
        """
        start_time = time.time()

        # Initialize working memory
        wm = WorkingMemory(event)

        logger.info(
            f"Starting reasoning for {event.source} event",
            extra={
                "event_id": event.event_id,
                "title": event.title,
                "initial_confidence": wm.overall_confidence,
            }
        )

        # Iterative reasoning loop
        while wm.needs_more_reasoning(
            threshold=self.confidence_threshold,
            max_passes=self.max_iterations
        ):
            pass_num = len(wm.reasoning_passes) + 1

            logger.debug(
                f"Starting pass {pass_num}",
                extra={
                    "current_confidence": wm.overall_confidence,
                    "target": self.confidence_threshold,
                }
            )

            # Execute appropriate pass
            if pass_num == 1:
                self._pass1_initial_analysis(wm)
            elif pass_num == 2:
                if self.enable_context:
                    self._pass2_context_enrichment(wm)
                else:
                    # Skip to Pass 3 if context disabled
                    self._pass3_deep_reasoning(wm)
            elif pass_num == 3:
                self._pass3_deep_reasoning(wm)
            elif pass_num == 4:
                if self.enable_validation:
                    self._pass4_validation(wm)
                else:
                    # Skip validation if disabled
                    break
            elif pass_num == 5:
                self._pass5_user_clarification(wm)
            else:
                # Safety: should never reach here due to max_passes check
                logger.warning(f"Unexpected pass number: {pass_num}")
                break

        # Finalize result
        duration = time.time() - start_time
        converged = wm.is_confident(self.confidence_threshold)

        # Extract final analysis (email-specific for now)
        final_analysis = self._extract_final_analysis(wm)

        result = ReasoningResult(
            working_memory=wm,
            final_analysis=final_analysis,
            reasoning_trace=wm.reasoning_passes,
            confidence=wm.overall_confidence,
            passes_executed=len(wm.reasoning_passes),
            total_duration_seconds=duration,
            converged=converged,
            uncertainties=wm.uncertainties,
            questions_for_user=self._extract_user_questions(wm),
        )

        logger.info(
            f"Reasoning complete: {result.passes_executed} passes, "
            f"{result.confidence:.1%} confidence, {duration:.1f}s",
            extra={
                "converged": converged,
                "final_action": final_analysis.action.value if final_analysis else None,
            }
        )

        return result

    # ========================================================================
    # PASS 1: INITIAL ANALYSIS
    # ========================================================================

    def _pass1_initial_analysis(self, wm: WorkingMemory) -> None:
        """
        Pass 1: Quick initial analysis without context

        Goal: Understand the event quickly
        Target Confidence: 60-70%
        Time Budget: 2-3 seconds
        Model: Haiku (fast and economical)

        Args:
            wm: Working memory to update
        """
        # Start pass
        wm.start_reasoning_pass(1, "initial_analysis")

        try:
            # Render template
            prompt = self.template_manager.render(
                "ai/pass1_initial",
                event=wm.event
            )

            # Call AI (Haiku for speed)
            response, usage = self.ai_router.analyze_with_prompt(
                prompt=prompt,
                model=AIModel.CLAUDE_HAIKU,
                system_prompt="You are Sancho, analyzing events quickly but accurately."
            )

            # Record in pass
            if wm.current_pass:
                wm.current_pass.ai_prompts.append(prompt[:500])  # Truncate for storage
                wm.current_pass.ai_responses.append(response[:500])

            # Parse response
            analysis = self._parse_pass1_response(response)

            if analysis:
                # Create hypothesis
                hypothesis = Hypothesis(
                    id="pass1_initial",
                    description=analysis.get("understanding", {}).get("summary", "Initial analysis"),
                    confidence=min(analysis.get("hypothesis", {}).get("confidence", 65) / 100.0, 0.75),
                    supporting_evidence=[
                        analysis.get("hypothesis", {}).get("reasoning", "")
                    ],
                    metadata={"pass": 1, "model": "haiku", "analysis": analysis}
                )

                wm.add_hypothesis(hypothesis, replace=True)
                wm.update_confidence(hypothesis.confidence)

                # Record insights
                if wm.current_pass:
                    wm.current_pass.insights.append(
                        analysis.get("understanding", {}).get("summary", "")
                    )

                logger.debug(
                    f"Pass 1 complete: {wm.overall_confidence:.1%} confidence",
                    extra={"hypothesis": hypothesis.description[:100]}
                )
            else:
                logger.warning("Pass 1: Failed to parse AI response")
                # Set conservative confidence
                wm.update_confidence(0.50)

        except Exception as e:
            logger.error(f"Pass 1 error: {e}", exc_info=True)
            wm.update_confidence(0.50)  # Conservative fallback

        finally:
            # Complete pass
            wm.complete_reasoning_pass()

    # ========================================================================
    # PASS 2: CONTEXT ENRICHMENT (STUB - Week 3)
    # ========================================================================

    def _pass2_context_enrichment(self, wm: WorkingMemory) -> None:
        """
        Pass 2: Context enrichment with Scapin knowledge

        Goal: Re-analyze with retrieved context
        Target Confidence: 75-85%
        Time Budget: 3-5 seconds
        Model: Sonnet (balanced)

        NOTE: This is a STUB for Phase 0.5 Week 3
        Currently just adds mock context and slight confidence boost

        Args:
            wm: Working memory to update
        """
        wm.start_reasoning_pass(2, "context_enrichment")

        try:
            # STUB: Mock context (Week 3 will implement real Passepartout integration)
            wm.add_context_simple(
                source="pkm_stub",
                type="note",
                content="Mock context - Passepartout integration coming in Week 3",
                relevance=0.5
            )

            # Slight confidence boost for mock
            current_confidence = wm.overall_confidence
            boosted = min(current_confidence + 0.05, 0.85)  # +5%, cap at 85%
            wm.update_confidence(boosted)

            if wm.current_pass:
                wm.current_pass.insights.append("Context enrichment (stub - Week 3 feature)")

            logger.debug(
                f"Pass 2 (stub) complete: {wm.overall_confidence:.1%} confidence"
            )

        except Exception as e:
            logger.error(f"Pass 2 error: {e}", exc_info=True)

        finally:
            wm.complete_reasoning_pass()

    # ========================================================================
    # PASS 3: DEEP REASONING
    # ========================================================================

    def _pass3_deep_reasoning(self, wm: WorkingMemory) -> None:
        """
        Pass 3: Deep multi-step reasoning

        Goal: Chain-of-thought, explore alternatives, validate logic
        Target Confidence: 85-92%
        Time Budget: 2-4 seconds
        Model: Sonnet (balanced power/cost)

        Args:
            wm: Working memory to update
        """
        wm.start_reasoning_pass(3, "deep_reasoning")

        try:
            # Get Pass 1/2 hypothesis
            pass2_hyp = wm.get_hypothesis("pass1_initial")
            if not pass2_hyp:
                logger.warning("Pass 3: No previous hypothesis found")
                wm.complete_reasoning_pass()
                return

            # Render template
            prompt = self.template_manager.render(
                "ai/pass3_deep",
                event=wm.event,
                pass2_confidence=wm.overall_confidence * 100,
                pass2_hypothesis=pass2_hyp.metadata.get("analysis", {})
            )

            # Call AI (Sonnet for deeper reasoning)
            response, usage = self.ai_router.analyze_with_prompt(
                prompt=prompt,
                model=AIModel.CLAUDE_SONNET,
                system_prompt="You are Sancho, performing deep multi-step reasoning."
            )

            # Record
            if wm.current_pass:
                wm.current_pass.ai_prompts.append(prompt[:500])
                wm.current_pass.ai_responses.append(response[:500])

            # Parse response
            analysis = self._parse_pass3_response(response)

            if analysis:
                # Create hypothesis
                validated_hyp = analysis.get("validated_hypothesis", {})
                hypothesis = Hypothesis(
                    id="pass3_deep",
                    description=validated_hyp.get("reasoning", "Deep reasoning analysis"),
                    confidence=min(validated_hyp.get("confidence", 88) / 100.0, 0.92),
                    supporting_evidence=[
                        validated_hyp.get("logic_chain", "")
                    ],
                    metadata={"pass": 3, "model": "sonnet", "analysis": analysis}
                )

                wm.add_hypothesis(hypothesis, replace=True)
                wm.update_confidence(hypothesis.confidence)

                # Add insights
                if wm.current_pass and "chain_of_thought" in analysis:
                    for step in analysis["chain_of_thought"].get("steps", []):
                        wm.current_pass.insights.append(step.get("conclusion", ""))

                logger.debug(
                    f"Pass 3 complete: {wm.overall_confidence:.1%} confidence",
                    extra={"logic_chain": validated_hyp.get("logic_chain", "")[:100]}
                )
            else:
                logger.warning("Pass 3: Failed to parse AI response")

        except Exception as e:
            logger.error(f"Pass 3 error: {e}", exc_info=True)

        finally:
            wm.complete_reasoning_pass()

    # ========================================================================
    # PASS 4: VALIDATION (STUB - Multi-Provider)
    # ========================================================================

    def _pass4_validation(self, wm: WorkingMemory) -> None:
        """
        Pass 4: Cross-provider validation/consensus

        Goal: Independent validation of reasoning
        Target Confidence: 90-96%
        Time Budget: 3-5 seconds
        Model: Sonnet (different provider for consensus)

        NOTE: This is a STUB for multi-provider validation
        Currently just adds slight confidence boost
        Real implementation in Phase 2.5

        Args:
            wm: Working memory to update
        """
        wm.start_reasoning_pass(4, "validation")

        try:
            # STUB: Mock validation (Phase 2.5 will implement real multi-provider)
            current_confidence = wm.overall_confidence
            boosted = min(current_confidence + 0.03, 0.96)  # +3%, cap at 96%
            wm.update_confidence(boosted)

            if wm.current_pass:
                wm.current_pass.insights.append("Validation (stub - Phase 2.5 feature)")

            logger.debug(
                f"Pass 4 (stub) complete: {wm.overall_confidence:.1%} confidence"
            )

        except Exception as e:
            logger.error(f"Pass 4 error: {e}", exc_info=True)

        finally:
            wm.complete_reasoning_pass()

    # ========================================================================
    # PASS 5: USER CLARIFICATION
    # ========================================================================

    def _pass5_user_clarification(self, wm: WorkingMemory) -> None:
        """
        Pass 5: Generate questions for user clarification

        Goal: Ask targeted questions to resolve uncertainty
        Target Confidence: 95-99%
        Time Budget: Async (user response required)
        Model: Sonnet

        NOTE: This generates questions but doesn't wait for answers
        The questions are stored in working memory for review queue

        Args:
            wm: Working memory to update
        """
        wm.start_reasoning_pass(5, "user_clarification")

        try:
            # Get current hypothesis
            current_hyp = wm.current_best_hypothesis
            if not current_hyp:
                logger.warning("Pass 5: No hypothesis to clarify")
                wm.complete_reasoning_pass()
                return

            # Render template
            prompt = self.template_manager.render(
                "ai/pass5_clarification",
                event=wm.event,
                current_confidence=wm.overall_confidence * 100,
                pass1_confidence=65,  # Simplified
                pass2_confidence=75,
                pass3_confidence=88,
                pass4_confidence=91,
                pass1_hypothesis=current_hyp.metadata.get("analysis", {}),
                pass2_hypothesis=current_hyp.metadata.get("analysis", {}),
                pass3_hypothesis=current_hyp.metadata.get("analysis", {}),
                pass4_consensus=current_hyp.metadata.get("analysis", {}),
            )

            # Call AI
            response, usage = self.ai_router.analyze_with_prompt(
                prompt=prompt,
                model=AIModel.CLAUDE_SONNET,
                system_prompt="You are Sancho, generating clarification questions for the user."
            )

            # Parse questions
            analysis = self._parse_pass5_response(response)

            if analysis and "clarification_questions" in analysis:
                questions = analysis["clarification_questions"]

                # Add to working memory
                for q in questions:
                    wm.add_question(q.get("question", ""))

                if wm.current_pass:
                    wm.current_pass.insights.append(
                        f"Generated {len(questions)} clarification questions"
                    )

                logger.debug(
                    f"Pass 5 complete: {len(questions)} questions generated"
                )
            else:
                logger.warning("Pass 5: Failed to parse questions")

        except Exception as e:
            logger.error(f"Pass 5 error: {e}", exc_info=True)

        finally:
            wm.complete_reasoning_pass()

    # ========================================================================
    # RESPONSE PARSING
    # ========================================================================

    def _parse_pass1_response(self, response: str) -> Optional[dict[str, Any]]:
        """Parse Pass 1 JSON response"""
        return self._extract_json(response)

    def _parse_pass3_response(self, response: str) -> Optional[dict[str, Any]]:
        """Parse Pass 3 JSON response"""
        return self._extract_json(response)

    def _parse_pass5_response(self, response: str) -> Optional[dict[str, Any]]:
        """Parse Pass 5 JSON response"""
        return self._extract_json(response)

    def _extract_json(self, text: str) -> Optional[dict[str, Any]]:
        """Extract and parse JSON from AI response"""
        try:
            # Try to find JSON in response
            start = text.find("{")
            end = text.rfind("}") + 1

            if start == -1 or end == 0:
                logger.warning("No JSON found in response")
                return None

            json_str = text[start:end]
            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected parsing error: {e}")
            return None

    # ========================================================================
    # FINAL ANALYSIS EXTRACTION
    # ========================================================================

    def _extract_final_analysis(self, wm: WorkingMemory) -> Optional[EmailAnalysis]:
        """
        Extract final EmailAnalysis from working memory

        This converts Sancho's reasoning into an EmailAnalysis object
        for backward compatibility with existing email processor.

        Args:
            wm: Working memory with reasoning results

        Returns:
            EmailAnalysis or None if extraction fails
        """
        try:
            # Get best hypothesis
            best_hyp = wm.current_best_hypothesis
            if not best_hyp:
                logger.warning("No hypothesis found for final analysis")
                return None

            # Extract from hypothesis metadata
            analysis_data = best_hyp.metadata.get("analysis", {})

            # Try to extract email-specific fields
            if "hypothesis" in analysis_data:
                hyp = analysis_data["hypothesis"]
                action_str = hyp.get("recommended_action", "queue")

                # Map to EmailAction
                action = EmailAction.QUEUE  # Safe default
                try:
                    action = EmailAction(action_str.lower())
                except ValueError:
                    logger.warning(f"Unknown action: {action_str}, using QUEUE")

                # Extract category
                category_data = analysis_data.get("category", {})
                category_str = category_data.get("main", "personal")
                category = EmailCategory.PERSONAL  # Safe default
                try:
                    category = EmailCategory(category_str.lower())
                except ValueError:
                    logger.warning(f"Unknown category: {category_str}")

                # Build EmailAnalysis
                return EmailAnalysis(
                    action=action,
                    category=category,
                    destination=hyp.get("destination"),
                    confidence=int(wm.overall_confidence * 100),
                    reasoning=best_hyp.description,
                    tags=analysis_data.get("entities_confirmed", []),
                    entities={},
                    omnifocus_task=analysis_data.get("omnifocus_task"),
                    needs_full_content=False
                )

            # Fallback: conservative defaults
            logger.warning("Using fallback EmailAnalysis")
            return EmailAnalysis(
                action=EmailAction.QUEUE,
                category=EmailCategory.PERSONAL,
                confidence=int(wm.overall_confidence * 100),
                reasoning=best_hyp.description,
            )

        except Exception as e:
            logger.error(f"Failed to extract final analysis: {e}", exc_info=True)
            return None

    def _extract_user_questions(self, wm: WorkingMemory) -> list[dict[str, Any]]:
        """Extract formatted user questions from working memory"""
        # For now, just return open questions as simple dicts
        return [
            {"question": q, "type": "open_ended"}
            for q in wm.open_questions
        ]


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    "ReasoningEngine",
    "ReasoningResult",
]
