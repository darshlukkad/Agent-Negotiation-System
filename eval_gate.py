#!/usr/bin/env python3
"""
eval_gate.py – HW6 Eval Gate Implementation

Usage:
    python eval_gate.py --hash        # Print SHA-256 hash of eval_set.jsonl
    python eval_gate.py --aa          # Auto-accept: run eval, save baseline.json
    python eval_gate.py --gate        # Gate mode: compare against baseline
    python eval_gate.py --eval        # Just run evaluation, print results
"""

import argparse
import hashlib
import json
import math
import os
import random
import re
import statistics
import sys
from pathlib import Path

# Import the system adapter
try:
    from system import answer
except ImportError:
    print("ERROR: Could not import 'answer' from system.py")
    sys.exit(1)


def compute_hash(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def load_eval_set(filepath: str) -> list[dict]:
    """Load evaluation cases from JSONL file."""
    cases = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def load_manifest(filepath: str) -> dict:
    """Load manifest configuration."""
    with open(filepath, "r") as f:
        return json.load(f)


def load_baseline(filepath: str) -> dict | None:
    """Load baseline results if they exist."""
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r") as f:
        return json.load(f)


def run_check(check: list, response: str) -> bool:
    """
    Run a single check against the response.

    Check format: [check_type, ...args]
    Supported checks:
        - ["contains", "text"] - response contains text (case-insensitive)
        - ["not_contains", "text"] - response does not contain text
        - ["regex", "pattern"] - response matches regex pattern
        - ["any_of", ["a", "b", "c"]] - response contains any of the strings
    """
    check_type = check[0]
    response_lower = response.lower()

    if check_type == "contains":
        return check[1].lower() in response_lower

    elif check_type == "not_contains":
        return check[1].lower() not in response_lower

    elif check_type == "regex":
        pattern = check[1]
        return bool(re.search(pattern, response, re.IGNORECASE))

    elif check_type == "any_of":
        options = check[1]
        return any(opt.lower() in response_lower for opt in options)

    else:
        print(f"WARNING: Unknown check type: {check_type}")
        return False


def evaluate_case(case: dict, seed: int = 0) -> dict:
    """
    Evaluate a single test case.

    Returns:
        dict with keys: id, category, passed, checks_passed, checks_total, response_length
    """
    question = case["question"]
    checks = case.get("checks", [])

    # Get response from system
    response = answer(question, seed=seed)

    # Run all checks
    checks_passed = sum(1 for check in checks if run_check(check, response))
    checks_total = len(checks)

    # Case passes if all checks pass
    passed = checks_passed == checks_total

    return {
        "id": case["id"],
        "category": case.get("category", "general"),
        "passed": passed,
        "checks_passed": checks_passed,
        "checks_total": checks_total,
        "response_length": len(response),
        "response": response  # Store for debugging
    }


def run_evaluation(eval_set: list[dict], runs: int = 1, seed_base: int = 0) -> dict:
    """
    Run full evaluation across multiple runs.

    Returns:
        dict with aggregate results
    """
    all_results = []
    category_results = {}

    for run in range(runs):
        seed = seed_base + run
        run_results = []

        for case in eval_set:
            result = evaluate_case(case, seed=seed)
            run_results.append(result)

            # Track by category
            cat = result["category"]
            if cat not in category_results:
                category_results[cat] = {"passed": 0, "total": 0}
            category_results[cat]["total"] += 1
            if result["passed"]:
                category_results[cat]["passed"] += 1

        all_results.append(run_results)

    # Calculate aggregate metrics
    pass_rates = []
    total_tokens = []

    for run_results in all_results:
        passed = sum(1 for r in run_results if r["passed"])
        total = len(run_results)
        pass_rates.append(passed / total if total > 0 else 0)
        total_tokens.append(sum(r["response_length"] for r in run_results))

    mean_pass_rate = statistics.mean(pass_rates) if pass_rates else 0
    std_pass_rate = statistics.stdev(pass_rates) if len(pass_rates) > 1 else 0
    mean_tokens = statistics.mean(total_tokens) if total_tokens else 0

    # Calculate category pass rates
    category_pass_rates = {}
    for cat, data in category_results.items():
        rate = data["passed"] / data["total"] if data["total"] > 0 else 0
        category_pass_rates[cat] = rate

    return {
        "runs": runs,
        "mean_pass_rate": mean_pass_rate,
        "std_pass_rate": std_pass_rate,
        "mean_tokens": mean_tokens,
        "category_pass_rates": category_pass_rates,
        "total_cases": len(eval_set),
        "detailed_results": all_results[0] if all_results else []  # First run details
    }


def save_baseline(results: dict, filepath: str):
    """Save evaluation results as baseline."""
    baseline = {
        "mean_pass_rate": results["mean_pass_rate"],
        "std_pass_rate": results["std_pass_rate"],
        "mean_tokens": results["mean_tokens"],
        "category_pass_rates": results["category_pass_rates"],
        "runs": results["runs"]
    }
    with open(filepath, "w") as f:
        json.dump(baseline, f, indent=2)
    print(f"Baseline saved to {filepath}")


def gate_check(results: dict, baseline: dict, manifest: dict) -> tuple[str, list[str]]:
    """
    Compare current results against baseline using gate criteria.

    Returns:
        (verdict, reasons) - verdict is "SHIP" or "BLOCK"
    """
    gate_config = manifest.get("gate", {})
    max_drop_sigma = gate_config.get("max_drop_sigma", 2.5)
    max_token_increase = gate_config.get("max_token_increase", 0.25)
    critical_categories = gate_config.get("critical", [])

    reasons = []
    verdict = "SHIP"

    # Check 1: Pass rate regression
    baseline_rate = baseline["mean_pass_rate"]
    current_rate = results["mean_pass_rate"]
    baseline_std = baseline.get("std_pass_rate", 0.05)

    # Prevent division by zero
    if baseline_std == 0:
        baseline_std = 0.05

    drop = baseline_rate - current_rate
    drop_sigma = drop / baseline_std if baseline_std > 0 else 0

    if drop_sigma > max_drop_sigma:
        verdict = "BLOCK"
        reasons.append(
            f"Pass rate dropped by {drop_sigma:.2f} sigma "
            f"(from {baseline_rate:.2%} to {current_rate:.2%})"
        )

    # Check 2: Token increase
    baseline_tokens = baseline.get("mean_tokens", results["mean_tokens"])
    current_tokens = results["mean_tokens"]

    if baseline_tokens > 0:
        token_increase = (current_tokens - baseline_tokens) / baseline_tokens
        if token_increase > max_token_increase:
            verdict = "BLOCK"
            reasons.append(
                f"Token count increased by {token_increase:.1%} "
                f"(from {baseline_tokens:.0f} to {current_tokens:.0f})"
            )

    # Check 3: Critical category failures
    for critical_cat in critical_categories:
        current_cat_rate = results["category_pass_rates"].get(critical_cat, 0)
        baseline_cat_rate = baseline.get("category_pass_rates", {}).get(critical_cat, 1.0)

        if current_cat_rate < baseline_cat_rate * 0.9:  # 10% tolerance
            verdict = "BLOCK"
            reasons.append(
                f"Critical category '{critical_cat}' regressed "
                f"(from {baseline_cat_rate:.2%} to {current_cat_rate:.2%})"
            )

    return verdict, reasons


def print_results(results: dict, verbose: bool = False):
    """Print evaluation results."""
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"Total cases: {results['total_cases']}")
    print(f"Runs: {results['runs']}")
    print(f"Mean pass rate: {results['mean_pass_rate']:.2%}")
    print(f"Std pass rate: {results['std_pass_rate']:.4f}")
    print(f"Mean tokens: {results['mean_tokens']:.0f}")

    print("\nCategory breakdown:")
    for cat, rate in sorted(results["category_pass_rates"].items()):
        print(f"  {cat}: {rate:.2%}")

    if verbose and results.get("detailed_results"):
        print("\nDetailed results:")
        for r in results["detailed_results"]:
            status = "✓" if r["passed"] else "✗"
            print(f"  {status} {r['id']}: {r['checks_passed']}/{r['checks_total']} checks")


def main():
    parser = argparse.ArgumentParser(description="HW6 Eval Gate")
    parser.add_argument("--hash", action="store_true", help="Print hash of eval_set.jsonl")
    parser.add_argument("--aa", action="store_true", help="Auto-accept: run eval, save baseline")
    parser.add_argument("--gate", action="store_true", help="Gate mode: compare against baseline")
    parser.add_argument("--eval", action="store_true", help="Just run evaluation")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # File paths
    eval_set_path = "eval_set.jsonl"
    manifest_path = "manifest.json"
    baseline_path = "baseline.json"

    # Verify files exist
    if not os.path.exists(eval_set_path):
        print(f"ERROR: {eval_set_path} not found")
        sys.exit(1)

    if args.hash:
        # Just print hash
        hash_value = compute_hash(eval_set_path)
        print(f"SHA-256: {hash_value}")
        return

    if not os.path.exists(manifest_path):
        print(f"ERROR: {manifest_path} not found")
        sys.exit(1)

    # Load data
    eval_set = load_eval_set(eval_set_path)
    manifest = load_manifest(manifest_path)

    # Verify hash matches manifest
    computed_hash = compute_hash(eval_set_path)
    manifest_hash = manifest.get("eval_set_hash", "")

    if computed_hash != manifest_hash:
        print(f"WARNING: eval_set hash mismatch!")
        print(f"  Computed: {computed_hash}")
        print(f"  Manifest: {manifest_hash}")

    # Get gate config
    gate_config = manifest.get("gate", {})
    runs = gate_config.get("runs", 5)

    if args.aa:
        # Auto-accept mode: run eval and save baseline
        print("Running evaluation (auto-accept mode)...")
        results = run_evaluation(eval_set, runs=runs)
        print_results(results, args.verbose)
        save_baseline(results, baseline_path)
        print("\n✓ Baseline established")

    elif args.gate:
        # Gate mode: compare against baseline
        baseline = load_baseline(baseline_path)
        if baseline is None:
            print(f"ERROR: {baseline_path} not found. Run --aa first.")
            sys.exit(1)

        print("Running evaluation (gate mode)...")
        results = run_evaluation(eval_set, runs=runs)
        print_results(results, args.verbose)

        verdict, reasons = gate_check(results, baseline, manifest)

        print("\n" + "=" * 60)
        print(f"GATE VERDICT: {verdict}")
        print("=" * 60)

        if reasons:
            print("Reasons:")
            for reason in reasons:
                print(f"  - {reason}")

        sys.exit(0 if verdict == "SHIP" else 1)

    elif args.eval:
        # Just run evaluation
        print("Running evaluation...")
        results = run_evaluation(eval_set, runs=1)
        print_results(results, verbose=True)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
