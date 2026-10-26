"""Agent spawner - creates appropriate agents based on negotiation context."""

from typing import Any
from .prompt_analyzer import NegotiationContext
from .agents import BaseAgent, CostAgent, SecurityAgent, PerformanceAgent


# Domain to agent type mapping
DOMAIN_AGENT_MAP = {
    "cloud-deployment": ["cost", "security", "performance"],
    "vendor-selection": ["cost", "security", "performance"],
    "hiring": ["cost", "security", "performance"],  # Simplified for MVP
    "technology-choice": ["cost", "security", "performance"],
    "general": ["cost", "security", "performance"],
}

# Agent type to class mapping
AGENT_CLASSES = {
    "cost": CostAgent,
    "security": SecurityAgent,
    "performance": PerformanceAgent,
}


class AgentSpawner:
    """Creates and configures agents based on negotiation context."""

    def __init__(self):
        self.agents: list[BaseAgent] = []

    def spawn_agents(self, context: NegotiationContext) -> list[BaseAgent]:
        """
        Create appropriate agents for the given context.

        Args:
            context: The negotiation context

        Returns:
            List of configured agents
        """
        agent_types = DOMAIN_AGENT_MAP.get(context.domain, DOMAIN_AGENT_MAP["general"])

        self.agents = []
        for agent_type in agent_types:
            agent_class = AGENT_CLASSES.get(agent_type)
            if agent_class:
                agent = agent_class(priority_weight=self._get_weight(agent_type, context))
                agent.set_constraints(context.constraints)
                self.agents.append(agent)

        return self.agents

    def _get_weight(self, agent_type: str, context: NegotiationContext) -> float:
        """
        Determine agent priority weight based on goals.

        Args:
            agent_type: The type of agent
            context: The negotiation context

        Returns:
            Priority weight (0.5 to 1.5)
        """
        # Default weight
        weight = 1.0

        # Adjust based on optimization goals
        for goal in context.optimization_goals:
            if agent_type == "cost" and "cost" in goal.lower():
                weight = 1.3
            elif agent_type == "security" and "security" in goal.lower():
                weight = 1.3
            elif agent_type == "performance" and "performance" in goal.lower():
                weight = 1.3

        # Increase weight if there's a constraint for this type
        if agent_type in context.constraints:
            weight = max(weight, 1.2)

        return weight

    def get_agents(self) -> list[BaseAgent]:
        """Return the spawned agents."""
        return self.agents

    def get_agent_by_type(self, agent_type: str) -> BaseAgent | None:
        """Get a specific agent by type."""
        for agent in self.agents:
            if agent.agent_type == agent_type:
                return agent
        return None
