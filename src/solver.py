"""Solver - generates final recommendations from negotiation results."""

from dataclasses import dataclass
from typing import Any
from .orchestrator import NegotiationResult
from .prompt_analyzer import NegotiationContext


@dataclass
class Solution:
    """Final solution from the negotiation process."""
    recommendation: str
    explanation: str
    confidence: float
    all_options_evaluated: list[dict[str, Any]]
    constraint_status: str
    negotiation_summary: str


class Solver:
    """Generates final solutions from negotiation results."""

    def solve(
        self,
        context: NegotiationContext,
        negotiation_result: NegotiationResult
    ) -> Solution:
        """
        Generate the final solution.

        Args:
            context: The original negotiation context
            negotiation_result: Results from the orchestrator

        Returns:
            Solution with recommendation and explanation
        """
        # Check for constraint violations
        has_violations = len(negotiation_result.constraint_violations) > 0

        # Build option evaluations summary
        all_options = self._aggregate_evaluations(negotiation_result)

        # Find best valid option
        valid_options = [opt for opt in all_options if opt.get("meets_constraints", True)]

        if not valid_options:
            return self._no_valid_options_solution(context, negotiation_result, all_options)

        # Sort by aggregate score
        valid_options.sort(key=lambda x: x.get("aggregate_score", 0), reverse=True)
        best_option = valid_options[0]

        # Calculate confidence based on consensus
        confidence = self._calculate_confidence(negotiation_result)

        # Build explanation
        explanation = self._build_explanation(
            best_option,
            context,
            negotiation_result,
            valid_options
        )

        # Build negotiation summary
        summary = self._build_summary(negotiation_result)

        constraint_status = "All constraints satisfied" if not has_violations else \
            f"Constraint violations detected: {', '.join(negotiation_result.constraint_violations)}"

        return Solution(
            recommendation=best_option["name"],
            explanation=explanation,
            confidence=confidence,
            all_options_evaluated=all_options,
            constraint_status=constraint_status,
            negotiation_summary=summary
        )

    def _aggregate_evaluations(self, result: NegotiationResult) -> list[dict[str, Any]]:
        """Aggregate evaluations from all agents."""
        option_scores: dict[str, dict[str, Any]] = {}

        for proposal in result.final_proposals:
            for eval in proposal.evaluations:
                name = eval.option_name
                if name not in option_scores:
                    option_scores[name] = {
                        "name": name,
                        "scores": {},
                        "meets_constraints": True,
                        "reasonings": []
                    }

                option_scores[name]["scores"][proposal.agent_type] = eval.score
                option_scores[name]["reasonings"].append(
                    f"{proposal.agent_type}: {eval.reasoning}"
                )

                if not eval.meets_constraints:
                    option_scores[name]["meets_constraints"] = False

        # Calculate aggregate scores
        for name, data in option_scores.items():
            scores = list(data["scores"].values())
            data["aggregate_score"] = sum(scores) / len(scores) if scores else 0

        return list(option_scores.values())

    def _calculate_confidence(self, result: NegotiationResult) -> float:
        """Calculate confidence score based on negotiation outcome."""
        if not result.final_proposals:
            return 0.0

        # Check agreement level
        preferred_options = [p.preferred_option for p in result.final_proposals]
        most_common = max(set(preferred_options), key=preferred_options.count)
        agreement_ratio = preferred_options.count(most_common) / len(preferred_options)

        # Factor in number of rounds (faster consensus = higher confidence)
        round_factor = 1.0 - (result.total_rounds - 1) * 0.1

        # Factor in constraint violations
        violation_penalty = 0.2 if result.constraint_violations else 0

        confidence = (agreement_ratio * 0.6 + round_factor * 0.4) - violation_penalty
        return max(0.0, min(1.0, confidence))

    def _build_explanation(
        self,
        best_option: dict[str, Any],
        context: NegotiationContext,
        result: NegotiationResult,
        valid_options: list[dict[str, Any]]
    ) -> str:
        """Build the explanation for the recommendation."""
        lines = []

        lines.append(f"**Recommendation: {best_option['name']}**")
        lines.append("")
        lines.append(f"After {result.total_rounds} round(s) of negotiation between "
                    f"{len(result.final_proposals)} agents, {best_option['name']} emerged "
                    f"as the best option with an aggregate score of {best_option['aggregate_score']:.1f}/10.")
        lines.append("")

        # Score breakdown
        lines.append("**Score Breakdown:**")
        for agent_type, score in best_option.get("scores", {}).items():
            lines.append(f"- {agent_type.capitalize()}: {score}/10")
        lines.append("")

        # Constraints
        if context.constraints:
            lines.append("**Constraints Satisfied:**")
            for constraint_type, constraint in context.constraints.items():
                lines.append(f"- {constraint_type}: {constraint}")
            lines.append("")

        # Alternatives
        if len(valid_options) > 1:
            lines.append("**Alternatives Considered:**")
            for alt in valid_options[1:3]:  # Top 2 alternatives
                lines.append(f"- {alt['name']}: {alt['aggregate_score']:.1f}/10")

        return "\n".join(lines)

    def _build_summary(self, result: NegotiationResult) -> str:
        """Build a summary of the negotiation process."""
        lines = []

        for round_result in result.rounds:
            lines.append(f"Round {round_result.round_number}:")

            for proposal in round_result.proposals:
                lines.append(f"  - {proposal.agent_type} proposed {proposal.preferred_option} "
                           f"(score: {proposal.score})")

            if round_result.challenges:
                lines.append(f"  - {len(round_result.challenges)} challenge(s) raised")

            if round_result.consensus_reached:
                lines.append("  - Consensus reached!")

        return "\n".join(lines)

    def _no_valid_options_solution(
        self,
        context: NegotiationContext,
        result: NegotiationResult,
        all_options: list[dict[str, Any]]
    ) -> Solution:
        """Generate solution when no options meet constraints."""
        explanation = (
            "**No Valid Options**\n\n"
            "None of the provided options satisfy all constraints. "
            "The constraints specified cannot be met with the available options.\n\n"
            "**Constraints:**\n"
        )

        for constraint_type, constraint in context.constraints.items():
            explanation += f"- {constraint_type}: {constraint}\n"

        explanation += "\n**Options Evaluated:**\n"
        for opt in all_options:
            explanation += f"- {opt['name']}: Does not meet constraints\n"

        return Solution(
            recommendation="No valid option",
            explanation=explanation,
            confidence=0.0,
            all_options_evaluated=all_options,
            constraint_status="CONSTRAINT VIOLATION: No options meet all constraints",
            negotiation_summary=self._build_summary(result)
        )
