"""Orchestrator - runs negotiation rounds between agents."""

from dataclasses import dataclass, field
from typing import Any
from .agents.base_agent import BaseAgent, Proposal, Challenge


@dataclass
class NegotiationRound:
    """Results from a single negotiation round."""
    round_number: int
    proposals: list[Proposal]
    challenges: list[Challenge]
    consensus_reached: bool = False


@dataclass
class NegotiationResult:
    """Final result of the negotiation process."""
    rounds: list[NegotiationRound]
    final_proposals: list[Proposal]
    consensus_option: str | None
    total_rounds: int
    constraint_violations: list[str] = field(default_factory=list)


class Orchestrator:
    """Orchestrates negotiation rounds between agents."""

    def __init__(self, max_rounds: int = 3, consensus_threshold: float = 0.8):
        """
        Initialize the orchestrator.

        Args:
            max_rounds: Maximum number of negotiation rounds
            consensus_threshold: Agreement level needed for consensus (0-1)
        """
        self.max_rounds = max_rounds
        self.consensus_threshold = consensus_threshold
        self.rounds: list[NegotiationRound] = []

    def run_negotiation(
        self,
        agents: list[BaseAgent],
        options: list[dict[str, Any]]
    ) -> NegotiationResult:
        """
        Run the full negotiation process.

        Args:
            agents: List of agents to participate
            options: Options to evaluate

        Returns:
            NegotiationResult with all rounds and final decision
        """
        self.rounds = []
        constraint_violations = []

        # Initial evaluation by all agents
        for agent in agents:
            agent.evaluate_all(options)

        for round_num in range(1, self.max_rounds + 1):
            round_result = self._run_round(agents, round_num)
            self.rounds.append(round_result)

            if round_result.consensus_reached:
                break

        # Collect final proposals
        final_proposals = [agent.propose() for agent in agents]

        # Check for constraint violations
        for proposal in final_proposals:
            for eval in proposal.evaluations:
                if not eval.meets_constraints:
                    constraint_violations.append(
                        f"{proposal.agent_type}: {eval.option_name} violates constraints"
                    )

        # Determine consensus option
        consensus_option = self._determine_consensus(final_proposals)

        return NegotiationResult(
            rounds=self.rounds,
            final_proposals=final_proposals,
            consensus_option=consensus_option,
            total_rounds=len(self.rounds),
            constraint_violations=constraint_violations
        )

    def _run_round(self, agents: list[BaseAgent], round_num: int) -> NegotiationRound:
        """Run a single negotiation round."""
        # Phase 1: Proposals
        proposals = [agent.propose() for agent in agents]

        # Phase 2: Challenges
        all_challenges = []
        for agent in agents:
            challenges = agent.challenge(proposals)
            all_challenges.extend(challenges)

        # Phase 3: Compromise
        for agent in agents:
            relevant_challenges = [c for c in all_challenges if c.target_proposal == agent.agent_type]
            agent.compromise(relevant_challenges)

        # Check for consensus
        consensus = self._check_consensus(proposals)

        return NegotiationRound(
            round_number=round_num,
            proposals=proposals,
            challenges=all_challenges,
            consensus_reached=consensus
        )

    def _check_consensus(self, proposals: list[Proposal]) -> bool:
        """Check if agents have reached consensus."""
        if not proposals:
            return False

        # Count votes for each option
        vote_counts: dict[str, int] = {}
        for proposal in proposals:
            opt = proposal.preferred_option
            vote_counts[opt] = vote_counts.get(opt, 0) + 1

        # Check if any option has enough votes
        total_agents = len(proposals)
        for option, votes in vote_counts.items():
            if votes / total_agents >= self.consensus_threshold:
                return True

        return False

    def _determine_consensus(self, proposals: list[Proposal]) -> str | None:
        """Determine the consensus option from final proposals."""
        if not proposals:
            return None

        # Weight votes by agent priority
        weighted_votes: dict[str, float] = {}
        for proposal in proposals:
            opt = proposal.preferred_option
            # Simple voting - each agent gets one vote
            weighted_votes[opt] = weighted_votes.get(opt, 0) + 1

        # Return option with most votes
        if weighted_votes:
            return max(weighted_votes.items(), key=lambda x: x[1])[0]

        return None


class MockOrchestrator(Orchestrator):
    """Deterministic orchestrator for testing."""

    def run_negotiation(
        self,
        agents: list[BaseAgent],
        options: list[dict[str, Any]]
    ) -> NegotiationResult:
        """Run deterministic negotiation for consistent eval results."""
        # Same logic as parent, but ensures deterministic behavior
        return super().run_negotiation(agents, options)
