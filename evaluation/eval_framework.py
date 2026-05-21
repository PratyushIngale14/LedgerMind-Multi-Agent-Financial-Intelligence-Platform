"""
Evaluation framework for LedgerMind.

Measures three properties of the multi-agent system:

1. ABSTENTION CORRECTNESS: When a question is outside an agent's specialty,
   does that agent correctly abstain? When a question is in-scope, does it
   respond rather than abstain?

2. CITATION COVERAGE: Do responding agents cite sources from the knowledge
   base, or do they answer without grounding?

3. CALCULATION GROUNDING: Do agents reference the precomputed numerical
   results in their reasoning, or do they invent figures?

These three metrics together approximate "hallucination rate" without
requiring a labeled ground-truth dataset for every test case.
"""

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TestCase:
    """A single evaluation test case."""
    id: str
    query: str
    expected_responding_agents: list[str]  # Agents that should NOT abstain
    expected_abstaining_agents: list[str]  # Agents that should abstain
    expected_citations_topics: list[str] = field(default_factory=list)  # KB topics that should be cited
    description: str = ""


# Golden test set: questions designed to test each agent's scoping correctness.
GOLDEN_TEST_CASES = [
    TestCase(
        id="tax_001",
        query="What is the 2025 contribution limit for a Roth IRA?",
        expected_responding_agents=["CA"],
        expected_abstaining_agents=["Analyst", "Risk", "Investment"],
        expected_citations_topics=["IRA Contribution Limits"],
        description="Pure tax compliance question. Only CA should respond.",
    ),
    TestCase(
        id="spending_001",
        query="How much did I spend on dining last month?",
        expected_responding_agents=["Analyst"],
        expected_abstaining_agents=["CA", "Risk", "Investment"],
        description="Pure spending analysis. Only Analyst should respond.",
    ),
    TestCase(
        id="anomaly_001",
        query="Are there any suspicious or duplicate transactions on my credit card?",
        expected_responding_agents=["Risk"],
        expected_abstaining_agents=["CA", "Analyst", "Investment"],
        expected_citations_topics=["Transaction Anomaly Detection", "Duplicate Charge Disputes"],
        description="Anomaly detection question. Only Risk should respond.",
    ),
    TestCase(
        id="portfolio_001",
        query="Is my portfolio too concentrated in any one sector?",
        expected_responding_agents=["Investment"],
        expected_abstaining_agents=["CA", "Analyst", "Risk"],
        expected_citations_topics=["Portfolio Diversification"],
        description="Pure portfolio question. Only Investment should respond.",
    ),
    TestCase(
        id="multi_001",
        query="Should I sell my AAPL shares to fund my IRA contribution this year?",
        expected_responding_agents=["CA", "Investment"],
        expected_abstaining_agents=["Analyst", "Risk"],
        expected_citations_topics=["Long-Term Capital Gains", "IRA Contribution"],
        description="Cross-cutting tax and investment question. CA and Investment respond.",
    ),
    TestCase(
        id="multi_002",
        query="Give me a full financial health review.",
        expected_responding_agents=["CA", "Analyst", "Risk", "Investment"],
        expected_abstaining_agents=[],
        description="Holistic question. All four should respond.",
    ),
]


@dataclass
class EvaluationResult:
    """Result of evaluating a single test case."""
    test_id: str
    passed: bool
    scoping_score: float
    citation_score: float
    calculation_grounding_score: float
    overall_score: float
    details: dict[str, Any]


def evaluate_test_case(test_case: TestCase, full_result: dict) -> EvaluationResult:
    """Evaluate a single test case against the orchestrator output."""
    agent_responses = {
        "CA": full_result.get("ca_response", {}),
        "Analyst": full_result.get("analyst_response", {}),
        "Risk": full_result.get("risk_response", {}),
        "Investment": full_result.get("investment_response", {}),
    }

    # SCOPING CORRECTNESS
    scoping_correct = 0
    scoping_total = 0
    scoping_detail = {}
    for agent, resp in agent_responses.items():
        abstained = resp.get("abstain", False)
        should_abstain = agent in test_case.expected_abstaining_agents
        should_respond = agent in test_case.expected_responding_agents

        if should_abstain:
            scoping_total += 1
            if abstained:
                scoping_correct += 1
                scoping_detail[agent] = "correctly abstained"
            else:
                scoping_detail[agent] = "incorrectly responded (should have abstained)"
        elif should_respond:
            scoping_total += 1
            if not abstained:
                scoping_correct += 1
                scoping_detail[agent] = "correctly responded"
            else:
                scoping_detail[agent] = "incorrectly abstained (should have responded)"

    scoping_score = scoping_correct / scoping_total if scoping_total else 1.0

    # CITATION COVERAGE
    expected_topics = set(t.lower() for t in test_case.expected_citations_topics)
    cited_topics = set()
    for resp in agent_responses.values():
        if not resp.get("abstain"):
            for cite in resp.get("citations", []):
                topic = cite.get("topic", "").lower()
                if topic:
                    cited_topics.add(topic)

    if expected_topics:
        matched = sum(1 for et in expected_topics if any(et in ct or ct in et for ct in cited_topics))
        citation_score = matched / len(expected_topics)
    else:
        citation_score = 1.0  # No required citations

    # CALCULATION GROUNDING
    # A responding agent should have at least one computed_value entry or cite
    # a flag from the precomputed analysis. Otherwise it may be ungrounded.
    grounding_correct = 0
    grounding_total = 0
    for agent in test_case.expected_responding_agents:
        resp = agent_responses.get(agent, {})
        if resp.get("abstain"):
            continue
        grounding_total += 1
        has_computed = len(resp.get("computed_values", [])) > 0
        has_flags = len(resp.get("flags", [])) > 0
        if has_computed or has_flags:
            grounding_correct += 1

    grounding_score = grounding_correct / grounding_total if grounding_total else 1.0

    overall = (scoping_score * 0.5) + (citation_score * 0.25) + (grounding_score * 0.25)

    return EvaluationResult(
        test_id=test_case.id,
        passed=overall >= 0.7,
        scoping_score=round(scoping_score, 2),
        citation_score=round(citation_score, 2),
        calculation_grounding_score=round(grounding_score, 2),
        overall_score=round(overall, 2),
        details={
            "scoping": scoping_detail,
            "cited_topics": sorted(list(cited_topics)),
            "expected_topics": sorted(list(expected_topics)),
        },
    )


def run_evaluation(orchestrator, financial_data: dict, test_cases: list[TestCase] | None = None) -> dict:
    """Run all test cases through the orchestrator and aggregate results."""
    if test_cases is None:
        test_cases = GOLDEN_TEST_CASES

    results = []
    for tc in test_cases:
        full = orchestrator.run(tc.query, financial_data)
        result = evaluate_test_case(tc, full)
        results.append(result)

    aggregate = {
        "num_tests": len(results),
        "num_passed": sum(1 for r in results if r.passed),
        "pass_rate": round(sum(1 for r in results if r.passed) / len(results), 2) if results else 0.0,
        "avg_scoping_score": round(sum(r.scoping_score for r in results) / len(results), 2) if results else 0.0,
        "avg_citation_score": round(sum(r.citation_score for r in results) / len(results), 2) if results else 0.0,
        "avg_calculation_grounding_score": round(sum(r.calculation_grounding_score for r in results) / len(results), 2) if results else 0.0,
        "avg_overall_score": round(sum(r.overall_score for r in results) / len(results), 2) if results else 0.0,
        "per_test": [
            {
                "test_id": r.test_id,
                "passed": r.passed,
                "overall_score": r.overall_score,
                "scoping_score": r.scoping_score,
                "citation_score": r.citation_score,
                "calculation_grounding_score": r.calculation_grounding_score,
                "details": r.details,
            }
            for r in results
        ],
    }

    return aggregate
