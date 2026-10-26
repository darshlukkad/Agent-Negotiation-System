# Agent Negotiation System

An AI-powered system where multiple agents with different optimization perspectives (Cost, Security, Performance) negotiate to find optimal solutions for complex decision-making scenarios.

## Overview

The Agent Negotiation System simulates a negotiation process between specialized AI agents, each optimizing for different objectives. This approach helps find balanced solutions that consider multiple stakeholder perspectives.

### Key Features

- **Multi-Agent Architecture**: Three specialized agents (Cost, Security, Performance)
- **Negotiation Protocol**: Multi-round negotiation with proposals, challenges, and compromises
- **Constraint Enforcement**: Hard constraints are strictly enforced
- **Dual Execution Modes**: Deterministic (for testing) and LLM-powered (for demos)
- **HW6 Compliance**: Full eval gate integration with baseline comparison

## Architecture

```
src/
├── prompt_analyzer.py     # Parses prompts, extracts context
├── agent_spawner.py       # Creates appropriate agents
├── orchestrator.py        # Runs negotiation rounds
├── solver.py              # Generates final recommendations
└── agents/
    ├── base_agent.py      # Base agent class
    ├── cost_agent.py      # Optimizes for cost
    ├── security_agent.py  # Optimizes for security
    └── performance_agent.py # Optimizes for performance
```

## Installation

```bash
# Clone the repository
cd agent-negotiation-system

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your OpenAI API key (optional, only for LLM mode)
```

## Usage

### Basic Usage

```python
from system import answer

question = """
Choose cloud deployment:
- AWS ($800/mo, security 7/10, performance 9/10)
- Azure ($750/mo, security 8/10, performance 7/10)
- GCP ($900/mo, security 9/10, performance 8/10)
Constraints: security >= 7, cost <= $1000
"""

response = answer(question, seed=42)
print(response)
```

### Running the Eval Gate

```bash
# Verify eval set hash
python eval_gate.py --hash

# Generate baseline (first time setup)
python eval_gate.py --aa

# Run gate check (CI mode)
python eval_gate.py --gate

# Run evaluation only (development)
python eval_gate.py --eval
```

### Execution Modes

**Deterministic Mode (Default)**
- Uses rule-based logic for consistent results
- Perfect for eval testing and CI pipelines
- Set `USE_LLM=false` or leave unset

**LLM Mode**
- Uses GPT-4o-mini for real AI-powered negotiations
- Requires OpenAI API key
- Set `USE_LLM=true`

## Eval Set Categories

1. **cloud-deployment** (12 cases): Cloud provider selection scenarios
2. **vendor-selection** (10 cases): Vendor comparison decisions
3. **constraint-enforcement** (8 cases): Critical constraint validation tests

## Gate Configuration

The eval gate uses these criteria (from `manifest.json`):

- **max_drop_sigma**: 2.5 (maximum allowed pass rate regression in standard deviations)
- **max_token_increase**: 0.25 (25% maximum token count increase)
- **critical**: ["constraint-enforcement"] (categories that cannot regress)

## Development

### Project Structure

| File | Purpose |
|------|---------|
| `system.py` | HW6 adapter entry point |
| `eval_gate.py` | Evaluation and gating logic |
| `eval_set.jsonl` | 30 test cases |
| `manifest.json` | Release configuration |
| `baseline.json` | Baseline metrics (generated) |

### Running Tests

```bash
# Quick test
python system.py

# Full evaluation
python eval_gate.py --eval -v
```

## CI/CD

The GitHub Actions workflow (`.github/workflows/eval-gate.yml`) runs automatically on:
- Push to main/master
- Pull requests to main/master

It verifies:
1. Eval set hash matches manifest
2. Gate check passes against baseline

## License

MIT
