"""Cost optimization agent."""

from typing import Any
from .base_agent import BaseAgent, Evaluation


class CostAgent(BaseAgent):
    """Agent that optimizes for cost efficiency."""

    def __init__(self, priority_weight: float = 1.0):
        super().__init__("cost", priority_weight)

    def evaluate(self, option: dict[str, Any]) -> Evaluation:
        """
        Evaluate an option based on cost efficiency.

        Scoring logic:
        - Lower cost = higher score
        - Considers cost relative to other metrics (value for money)
        """
        name = option.get("name", "Unknown")
        cost = option.get("cost", 0)

        # Check cost constraint
        meets_constraints = self.check_constraint("cost", cost)

        # Score inversely proportional to cost
        # Normalize assuming costs between $0-$2000/mo
        if cost <= 0:
            score = 10.0
        elif cost >= 2000:
            score = 2.0
        else:
            # Linear scale: $0 = 10, $2000 = 2
            score = 10 - (cost / 2000) * 8

        # Bonus for good value (if performance/security data available)
        security = option.get("security", 5)
        performance = option.get("performance", 5)
        value_ratio = (security + performance) / 2 / max(cost / 100, 1)
        value_bonus = min(1.0, value_ratio * 0.5)

        final_score = min(10, score + value_bonus)

        constraint_note = "" if meets_constraints else " [EXCEEDS COST CONSTRAINT]"
        reasoning = (
            f"{name} costs ${cost}/mo. "
            f"Cost efficiency score: {score:.1f}/10. "
            f"Value bonus: +{value_bonus:.1f} for security/performance ratio."
            f"{constraint_note}"
        )

        return Evaluation(
            option_name=name,
            score=round(final_score, 1),
            reasoning=reasoning,
            meets_constraints=meets_constraints
        )
