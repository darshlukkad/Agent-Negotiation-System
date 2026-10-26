"""Security optimization agent."""

from typing import Any
from .base_agent import BaseAgent, Evaluation


class SecurityAgent(BaseAgent):
    """Agent that optimizes for security."""

    def __init__(self, priority_weight: float = 1.0):
        super().__init__("security", priority_weight)

    def evaluate(self, option: dict[str, Any]) -> Evaluation:
        """
        Evaluate an option based on security.

        Scoring logic:
        - Direct mapping of security rating to score
        - Penalties for low security regardless of other factors
        """
        name = option.get("name", "Unknown")
        security = option.get("security", 5)

        # Check security constraint
        meets_constraints = self.check_constraint("security", security)

        # Direct score from security rating
        base_score = security

        # Penalty for security below 7 (considered minimum acceptable)
        if security < 7:
            penalty = (7 - security) * 0.5
            base_score -= penalty

        # Bonus for excellent security (9+)
        if security >= 9:
            base_score += 0.5

        final_score = max(0, min(10, base_score))

        constraint_note = "" if meets_constraints else " [BELOW SECURITY CONSTRAINT]"
        reasoning = (
            f"{name} has security rating {security}/10. "
            f"{'Excellent' if security >= 9 else 'Good' if security >= 7 else 'Concerning'} security posture."
            f"{constraint_note}"
        )

        return Evaluation(
            option_name=name,
            score=round(final_score, 1),
            reasoning=reasoning,
            meets_constraints=meets_constraints
        )
