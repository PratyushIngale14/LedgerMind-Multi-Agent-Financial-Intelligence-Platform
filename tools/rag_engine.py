"""
Mock RAG Engine for LedgerMind.

In a production system this would use a vector database (Pinecone, Chroma, etc.)
to retrieve semantically relevant chunks from a tax and compliance knowledge
base. For this implementation, we mock the retrieval with keyword matching
against a curated JSON knowledge base.

The interface is designed to be drop-in replaceable with a real RAG system.
Each retrieval returns the matched chunks plus source authority metadata so
agents can cite their sources.
"""

import json
from pathlib import Path
from typing import Any


class MockRAGEngine:
    """
    Knowledge retrieval interface. Returns relevant chunks from the tax and
    compliance knowledge base based on keyword matching. Each result includes
    the source citation and an authority tier so the downstream agents can
    weight evidence appropriately.
    """

    def __init__(self, kb_path: str = "./knowledge_base/tax_and_compliance_kb.json"):
        self.kb_path = Path(kb_path)
        with open(self.kb_path, "r") as f:
            self.kb: dict[str, dict] = json.load(f)

        # Build a simple inverted index of topic keywords for matching
        self.topic_keywords: dict[str, list[str]] = {
            "ira_contribution_limits_2025": ["ira", "roth", "traditional ira", "contribution limit", "retirement"],
            "401k_contribution_limits_2025": ["401k", "401(k)", "employer match", "retirement plan", "contribution"],
            "capital_gains_long_term": ["capital gains", "long-term", "selling stock", "sell shares", "tax on gains"],
            "capital_gains_short_term": ["short-term", "short term gains", "sell within a year"],
            "wash_sale_rule": ["wash sale", "tax loss", "harvesting", "sell at a loss"],
            "student_loan_interest_deduction": ["student loan", "loan interest", "education loan deduction"],
            "f1_opt_tax_status": ["opt", "f-1", "f1 visa", "nonresident", "fica", "international student"],
            "diversification_guidance": ["diversification", "concentration", "allocation", "asset allocation"],
            "emergency_fund_guidance": ["emergency fund", "savings", "rainy day", "liquid savings"],
            "duplicate_charge_dispute": ["duplicate", "duplicate charge", "dispute", "billing error"],
            "expense_ratio_guidance": ["expense ratio", "fund fees", "etf cost", "fund expenses"],
            "anomaly_detection_principles": ["anomaly", "fraud", "suspicious", "outlier", "unusual"],
        }

    def retrieve(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """
        Retrieve the top_k most relevant knowledge chunks for a query.

        Args:
            query: Natural language query from an agent.
            top_k: Maximum number of chunks to return.

        Returns:
            List of dicts with keys: topic, content, source, authority_tier, score.
        """
        query_lower = query.lower()
        scored: list[tuple[float, str]] = []

        for kb_key, keywords in self.topic_keywords.items():
            score = sum(2 if kw in query_lower else 0 for kw in keywords)
            # Bonus for exact topic word match
            topic_words = self.kb[kb_key]["topic"].lower().split()
            score += sum(1 for w in topic_words if w in query_lower)
            if score > 0:
                scored.append((score, kb_key))

        scored.sort(reverse=True)
        results = []
        for score, kb_key in scored[:top_k]:
            entry = self.kb[kb_key].copy()
            entry["score"] = score
            entry["kb_id"] = kb_key
            results.append(entry)

        return results

    def get_by_topic(self, topic_id: str) -> dict[str, Any] | None:
        """Direct lookup by knowledge base ID."""
        return self.kb.get(topic_id)


if __name__ == "__main__":
    rag = MockRAGEngine()
    test_queries = [
        "What's the IRA contribution limit?",
        "Am I overconcentrated in tech?",
        "Are there duplicate charges in my transactions?",
        "Do I owe FICA on my OPT salary?",
    ]
    for q in test_queries:
        print(f"\nQuery: {q}")
        results = rag.retrieve(q, top_k=2)
        for r in results:
            print(f"  [{r['authority_tier']}] {r['topic']} (score: {r['score']})")
