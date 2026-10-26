"""Performance optimization agent."""

from typing import Any
from .base_agent import BaseAgent, Evaluation


class PerformanceAgent(BaseAgent):
    """Agent that optimizes for performance."""

    def __init__(self, priority_weight: float = 1.0):
        super().__init__("performance", priority_weight)

    def evaluate(self, option: dict[str, Any]) -> Evaluation:
        """
        Evaluate an option based on performance.

        Scoring logic:
        - Direct mapping of performance rating to score
        - Considers performance relative to cost (efficiency)
        """
        name = option.get("name", "Unknown")
        performance = option.get("performance", 5)
        cost = option.get("cost", 500)

        # Check performance constraint
        meets_constraints = self.check_constraint("performance", performance)

        # Direct score from performance rating
        base_score = performance

        # Efficiency bonus: good performance at lower cost
        if cost > 0:
            efficiency = performance / (cost / 500)  # Normalize to $500 baseline
            if efficiency > 1.2:
                base_score += 0.5

        # Penalty for performance below 6
        if performance < 6:
            penalty = (6 - performance) * 0.3
            base_score -= penalty

        final_score = max(0, min(10, base_score))

        constraint_note = "" if meets_constraints else " [BELOW PERFORMANCE CONSTRAINT]"
        reasoning = (
            f"{name} has performance rating {performance}/10. "
            f"{'Excellent' if performance >= 9 else 'Good' if performance >= 7 else 'Adequate' if performance >= 5 else 'Poor'} performance."
            f"{constraint_note}"
        )

        return Evaluation(
            option_name=name,
            score=round(final_score, 1),
            reasoning=reasoning,
            meets_constraints=meets_constraints
        )
