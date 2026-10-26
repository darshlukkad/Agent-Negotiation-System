"""Prompt analyzer - parses input prompts to extract negotiation context."""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Option:
    """A single option to be evaluated."""
    name: str
    cost: float = 0
    security: float = 5
    performance: float = 5
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class NegotiationContext:
    """Structured context extracted from a prompt."""
    domain: str  # cloud-deployment, vendor-selection, hiring, etc.
    options: list[Option]
    constraints: dict[str, dict[str, float]]  # e.g., {"cost": {"max": 1000}}
    optimization_goals: list[str]  # e.g., ["minimize cost", "maximize security"]
    raw_prompt: str


class PromptAnalyzer:
    """Analyzes prompts to extract structured negotiation context."""

    # Domain keywords mapping
    DOMAIN_KEYWORDS = {
        "cloud-deployment": ["cloud", "aws", "azure", "gcp", "deployment", "hosting", "infrastructure"],
        "vendor-selection": ["vendor", "supplier", "provider", "partner", "service provider"],
        "hiring": ["hire", "candidate", "employee", "recruit", "talent"],
        "technology-choice": ["technology", "framework", "library", "tool", "stack"],
    }

    def analyze(self, prompt: str) -> NegotiationContext:
        """
        Analyze a prompt and extract negotiation context.

        Args:
            prompt: The input prompt to analyze

        Returns:
            NegotiationContext with extracted information
        """
        domain = self._detect_domain(prompt)
        options = self._extract_options(prompt)
        constraints = self._extract_constraints(prompt)
        goals = self._extract_goals(prompt)

        return NegotiationContext(
            domain=domain,
            options=options,
            constraints=constraints,
            optimization_goals=goals,
            raw_prompt=prompt
        )

    def _detect_domain(self, prompt: str) -> str:
        """Detect the problem domain from the prompt."""
        prompt_lower = prompt.lower()

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(kw in prompt_lower for kw in keywords):
                return domain

        return "general"

    def _extract_options(self, prompt: str) -> list[Option]:
        """Extract options from the prompt."""
        options = []

        # Pattern for "Vendor A ($400/mo, security 7/10, performance 7/10)" format
        vendor_full_pattern = r'(Vendor\s+\w+)\s*\(\$(\d+)(?:/mo)?,?\s*security\s+(\d+)/10,?\s*performance\s+(\d+)/10\)'
        vendor_full_matches = re.findall(vendor_full_pattern, prompt, re.IGNORECASE)

        for match in vendor_full_matches:
            name, cost, security, performance = match
            options.append(Option(
                name=name,
                cost=float(cost),
                security=float(security),
                performance=float(performance)
            ))

        # Pattern for cloud options like "AWS ($800/mo, security 7/10, performance 9/10)"
        # Only match single words (not "Vendor X" which was already handled)
        cloud_pattern = r'(?<![Vv]endor\s)(\b(?:AWS|Azure|GCP|Option\s+\w)\b)\s*\(\$(\d+)(?:/mo)?,?\s*security\s+(\d+)/10,?\s*performance\s+(\d+)/10\)'
        matches = re.findall(cloud_pattern, prompt, re.IGNORECASE)

        for match in matches:
            name, cost, security, performance = match
            # Skip if already found (case-insensitive check)
            if not any(o.name.lower() == name.lower() for o in options):
                options.append(Option(
                    name=name,
                    cost=float(cost),
                    security=float(security),
                    performance=float(performance)
                ))

        # Pattern for simpler options like "Option A ($1500/mo, security 10/10)"
        simple_pattern = r'(Option\s+\w+)\s*\(\$(\d+)(?:/mo)?,?\s*security\s+(\d+)/10\)'
        simple_matches = re.findall(simple_pattern, prompt, re.IGNORECASE)

        for match in simple_matches:
            name, cost, security = match
            # Skip if already found
            if not any(o.name.lower() == name.lower() for o in options):
                options.append(Option(
                    name=name,
                    cost=float(cost),
                    security=float(security),
                    performance=5.0  # Default
                ))

        # Pattern for vendor with only security: "Vendor A ($500/mo, security 8/10)"
        vendor_security_pattern = r'(Vendor\s+\w+)\s*\(\$(\d+)(?:/mo)?,?\s*security\s+(\d+)/10\)'
        vendor_security_matches = re.findall(vendor_security_pattern, prompt, re.IGNORECASE)

        for match in vendor_security_matches:
            name, cost, security = match
            if not any(o.name.lower() == name.lower() for o in options):
                options.append(Option(
                    name=name,
                    cost=float(cost),
                    security=float(security),
                    performance=5.0  # Default
                ))

        # If no options found, create generic ones
        if not options:
            options = [
                Option(name="Option A"),
                Option(name="Option B"),
                Option(name="Option C"),
            ]

        return options

    def _extract_constraints(self, prompt: str) -> dict[str, dict[str, float]]:
        """Extract hard constraints from the prompt."""
        constraints = {}

        # Cost constraints
        cost_max_pattern = r'cost\s*<=?\s*\$?(\d+)'
        cost_max_match = re.search(cost_max_pattern, prompt, re.IGNORECASE)
        if cost_max_match:
            constraints["cost"] = {"max": float(cost_max_match.group(1))}

        cost_min_pattern = r'cost\s*>=?\s*\$?(\d+)'
        cost_min_match = re.search(cost_min_pattern, prompt, re.IGNORECASE)
        if cost_min_match:
            if "cost" not in constraints:
                constraints["cost"] = {}
            constraints["cost"]["min"] = float(cost_min_match.group(1))

        # Security constraints
        security_min_pattern = r'security\s*>=?\s*(\d+)'
        security_min_match = re.search(security_min_pattern, prompt, re.IGNORECASE)
        if security_min_match:
            constraints["security"] = {"min": float(security_min_match.group(1))}

        # Performance constraints
        perf_min_pattern = r'performance\s*>=?\s*(\d+)'
        perf_min_match = re.search(perf_min_pattern, prompt, re.IGNORECASE)
        if perf_min_match:
            constraints["performance"] = {"min": float(perf_min_match.group(1))}

        return constraints

    def _extract_goals(self, prompt: str) -> list[str]:
        """Extract optimization goals from the prompt."""
        goals = []
        prompt_lower = prompt.lower()

        if "cost" in prompt_lower or "budget" in prompt_lower or "cheap" in prompt_lower:
            goals.append("minimize cost")

        if "security" in prompt_lower or "secure" in prompt_lower:
            goals.append("maximize security")

        if "performance" in prompt_lower or "fast" in prompt_lower or "speed" in prompt_lower:
            goals.append("maximize performance")

        if not goals:
            goals = ["balanced optimization"]

        return goals
