"""
Standalone evaluation runner for LedgerMind.

Loads sample data, runs the golden test cases through the orchestrator,
and prints metrics. Use this to demonstrate reliability and hallucination
metrics in your portfolio.

Run:
    python run_evaluation.py
"""

import json
import os
import sys
from pathlib import Path

import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent))

from agents.orchestrator import Orchestrator
from evaluation.eval_framework import GOLDEN_TEST_CASES, run_evaluation
from tools.llm_client import LLMClient
from tools.rag_engine import MockRAGEngine
from utils.audit_log import AuditLogger
from utils.data_generator import save_all


def load_data():
    sample_dir = Path("./sample_data")
    if not (sample_dir / "portfolio.json").exists():
        save_all(output_dir=str(sample_dir))

    bank = pd.read_csv(sample_dir / "bank_transactions.csv", parse_dates=["date"])
    credit_card = pd.read_csv(sample_dir / "credit_card_transactions.csv", parse_dates=["date"])
    with open(sample_dir / "bills.json") as f:
        bills = json.load(f)
    with open(sample_dir / "loans.json") as f:
        loans = json.load(f)
    with open(sample_dir / "portfolio.json") as f:
        portfolio = json.load(f)
    with open(sample_dir / "income.json") as f:
        income = json.load(f)
    with open(sample_dir / "timeline.json") as f:
        timeline = json.load(f)

    return {
        "bank": bank,
        "credit_card": credit_card,
        "bills": bills,
        "loans": loans,
        "portfolio": portfolio,
        "income": income,
        "timeline": timeline,
    }


def main():
    print("=" * 70)
    print("LedgerMind Evaluation")
    print("=" * 70)
    print()

    financial_data = load_data()
    print(f"Loaded {len(financial_data['credit_card'])} credit card transactions")
    print(f"Portfolio value: ${financial_data['portfolio']['total_account_value']:,.2f}")
    print()

    llm = LLMClient()
    rag = MockRAGEngine()
    audit = AuditLogger(log_dir="./audit_logs/eval")
    orchestrator = Orchestrator(llm, rag, audit)

    print(f"Running {len(GOLDEN_TEST_CASES)} test cases...")
    print()

    results = run_evaluation(orchestrator, financial_data, GOLDEN_TEST_CASES)

    print("=" * 70)
    print("AGGREGATE RESULTS")
    print("=" * 70)
    print(f"Tests run:              {results['num_tests']}")
    print(f"Tests passed:           {results['num_passed']}")
    print(f"Pass rate:              {results['pass_rate']:.0%}")
    print(f"Avg scoping score:      {results['avg_scoping_score']:.0%}")
    print(f"Avg citation score:     {results['avg_citation_score']:.0%}")
    print(f"Avg calc grounding:     {results['avg_calculation_grounding_score']:.0%}")
    print(f"Avg overall score:      {results['avg_overall_score']:.0%}")
    print()

    print("=" * 70)
    print("PER-TEST RESULTS")
    print("=" * 70)
    for test in results["per_test"]:
        status = "PASS" if test["passed"] else "FAIL"
        print(f"[{status}] {test['test_id']}: overall {test['overall_score']:.0%} "
              f"(scoping {test['scoping_score']:.0%}, "
              f"citation {test['citation_score']:.0%}, "
              f"grounding {test['calculation_grounding_score']:.0%})")
        if not test["passed"]:
            for agent, outcome in test["details"]["scoping"].items():
                if "incorrectly" in outcome:
                    print(f"        {agent}: {outcome}")

    # Save full results
    results_path = Path("./audit_logs/eval/evaluation_results.json")
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print()
    print(f"Full results saved to {results_path}")


if __name__ == "__main__":
    main()