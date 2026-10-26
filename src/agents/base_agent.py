"""Base agent class for the negotiation system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class Evaluation:
    """Result of an agent evaluating an option."""
    option_name: str
    score: float  # 0-10 scale
    reasoning: str
    meets_constraints: bool = True


@dataclass
class Proposal:
    """An agent's proposal for the best option."""
    agent_type: str
    preferred_option: str
    score: float
    reasoning: str
    evaluations: list[Evaluation]


@dataclass
class Challenge:
    """An agent's challenge to another proposal."""
    challenger: str
    target_proposal: str
    critique: str
    suggested_adjustment: float


class BaseAgent(ABC):
    """Abstract base class for negotiation agents."""

    def __init__(self, agent_type: str, priority_weight: float = 1.0):
        """
        Initialize the agent.

        Args:
            agent_type: Type identifier for this agent (e.g., 'cost', 'security')
            priority_weight: Weight of this agent's scores in final calculation
        """
        self.agent_type = agent_type
        self.priority_weight = priority_weight
        self.constraints: dict[str, Any] = {}
        self.evaluations: list[Evaluation] = []

    def set_constraints(self, constraints: dict[str, Any]) -> None:
        """Set constraints that must be respected."""
        self.constraints = constraints

    @abstractmethod
    def evaluate(self, option: dict[str, Any]) -> Evaluation:
        """
        Evaluate a single option.

        Args:
            option: Dictionary containing option details

        Returns:
            Evaluation with score and reasoning
        """
        pass

    def evaluate_all(self, options: list[dict[str, Any]]) -> list[Evaluation]:
        """Evaluate all options and store results."""
        self.evaluations = [self.evaluate(opt) for opt in options]
        return self.evaluations

    def propose(self) -> Proposal:
        """
        Propose the best option based on evaluations.

        Returns:
            Proposal with preferred option and reasoning
        """
        if not self.evaluations:
            raise ValueError("Must evaluate options before proposing")

        # Filter to only options that meet constraints
        valid_evals = [e for e in self.evaluations if e.meets_constraints]

        if not valid_evals:
            # If no options meet constraints, still pick best but note the issue
            best = max(self.evaluations, key=lambda e: e.score)
            return Proposal(
                agent_type=self.agent_type,
                preferred_option=best.option_name,
                score=best.score,
                reasoning=f"WARNING: No options fully meet constraints. Best available: {best.reasoning}",
                evaluations=self.evaluations
            )

        best = max(valid_evals, key=lambda e: e.score)
        return Proposal(
            agent_type=self.agent_type,
            preferred_option=best.option_name,
            score=best.score,
            reasoning=best.reasoning,
            evaluations=self.evaluations
        )

    def challenge(self, other_proposals: list[Proposal]) -> list[Challenge]:
        """
        Challenge other agents' proposals.

        Args:
            other_proposals: Proposals from other agents

        Returns:
            List of challenges to other proposals
        """
        challenges = []
        my_proposal = self.propose()

        for proposal in other_proposals:
            if proposal.agent_type == self.agent_type:
                continue

            if proposal.preferred_option != my_proposal.preferred_option:
                # Find our evaluation of their preferred option
                our_eval = next(
                    (e for e in self.evaluations if e.option_name == proposal.preferred_option),
                    None
                )

                if our_eval and our_eval.score < my_proposal.score:
                    challenges.append(Challenge(
                        challenger=self.agent_type,
                        target_proposal=proposal.agent_type,
                        critique=f"From {self.agent_type} perspective, {proposal.preferred_option} "
                                f"scores {our_eval.score:.1f} vs {my_proposal.preferred_option} at {my_proposal.score:.1f}",
                        suggested_adjustment=-0.5
                    ))

        return challenges

    def compromise(self, feedback: list[Challenge]) -> None:
        """
        Adjust evaluations based on feedback from other agents.

        Args:
            feedback: Challenges from other agents
        """
        # Apply modest adjustments based on valid feedback
        for challenge in feedback:
            if challenge.target_proposal == self.agent_type:
                # Consider the feedback but maintain core priorities
                adjustment = challenge.suggested_adjustment * 0.3  # Partial acceptance
                for eval in self.evaluations:
                    if eval.option_name != self.propose().preferred_option:
                        eval.score = min(10, max(0, eval.score - adjustment))

    def check_constraint(self, constraint_type: str, value: Any) -> bool:
        """
        Check if a value meets the constraint.

        Args:
            constraint_type: Type of constraint (e.g., 'cost', 'security')
            value: Value to check

        Returns:
            True if constraint is met
        """
        if constraint_type not in self.constraints:
            return True

        constraint = self.constraints[constraint_type]

        if isinstance(constraint, dict):
            if 'min' in constraint and value < constraint['min']:
                return False
            if 'max' in constraint and value > constraint['max']:
                return False

        return True
