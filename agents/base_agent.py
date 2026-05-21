"""
Base specialist agent for LedgerMind.

All four specialists (CA, Analyst, Risk, Investment) inherit from this class.
Each agent prepares its own data context, performs RAG retrieval, calls the
LLM, validates the response, and logs everything to the audit layer.
"""

import time
from typing import Any

from tools.llm_client import LLMClient
from tools.rag_engine import MockRAGEngine
from utils.audit_log import AuditLogger


class SpecialistAgent:
    """Base class for all specialist agents."""

    name: str = "BaseAgent"
    system_prompt: str = ""

    def __init__(self, llm: LLMClient, rag: MockRAGEngine, audit: AuditLogger):
        self.llm = llm
        self.rag = rag
        self.audit = audit

    def build_context(self, query: str, financial_data: dict) -> dict[str, Any]:
        """Override in subclass: prepare the data context this agent needs."""
        raise NotImplementedError

    def build_rag_query(self, query: str) -> str:
        """Override in subclass: build a knowledge base retrieval query."""
        return query

    def respond(self, query: str, financial_data: dict) -> dict[str, Any]:
        """Main entrypoint. Returns the agent's parsed JSON response."""
        # Retrieval
        rag_query = self.build_rag_query(query)
        retrieved = self.rag.retrieve(rag_query, top_k=3)
        self.audit.log_rag_retrieval(self.name, rag_query, retrieved)

        # Context preparation
        context = self.build_context(query, financial_data)

        # Build user message
        user_message = self._format_user_message(query, context, retrieved)

        # LLM call
        start = time.time()
        response = self.llm.complete_json(
            system_prompt=self.system_prompt,
            user_message=user_message,
        )
        latency_ms = (time.time() - start) * 1000

        parsed = response.get("parsed", {})

        # Validate response shape
        validated = self._validate_response(parsed)

        # Apply uncertainty gate
        gated = self._uncertainty_gate(validated)
        if gated["gated"]:
            self.audit.log_uncertainty_gate(self.name, True, gated["reason"])
            validated["abstain"] = True
            validated["abstain_reason"] = gated["reason"]
            validated["confidence"] = min(validated.get("confidence", 0.0), 0.3)

        # Log final agent response
        self.audit.log_agent_response(self.name, validated, latency_ms)

        validated["_meta"] = {
            "agent": self.name,
            "latency_ms": round(latency_ms, 1),
            "tokens": response.get("usage"),
            "mock": response.get("mock", False),
        }
        return validated

    def _format_user_message(self, query: str, context: dict, retrieved: list[dict]) -> str:
        """Format the user message sent to the LLM."""
        retrieved_block = "\n".join([
            f"- [{r['authority_tier']}] {r['topic']}: {r['content']} (Source: {r['source']})"
            for r in retrieved
        ]) or "No relevant knowledge base entries retrieved."

        # Context can be large; format it compactly
        context_lines = []
        for k, v in context.items():
            context_lines.append(f"{k}:\n{v}")
        context_block = "\n\n".join(context_lines) if context_lines else "No additional context."

        return (
            f"USER QUESTION:\n{query}\n\n"
            f"RETRIEVED KNOWLEDGE BASE ENTRIES:\n{retrieved_block}\n\n"
            f"FINANCIAL DATA CONTEXT:\n{context_block}\n\n"
            f"Respond with a single JSON object per your output schema."
        )

    def _validate_response(self, parsed: dict) -> dict:
        """Ensure the parsed response has the required fields with sensible defaults."""
        if parsed.get("parse_error"):
            return {
                "verdict": "Unable to produce a structured response",
                "confidence": 0.0,
                "abstain": True,
                "abstain_reason": "Response failed to parse as JSON",
                "reasoning": parsed.get("raw_content", "")[:500],
                "citations": [],
                "computed_values": [],
                "flags": ["parse_error"],
            }

        defaults = {
            "verdict": "",
            "confidence": 0.0,
            "abstain": False,
            "abstain_reason": "",
            "reasoning": "",
            "citations": [],
            "computed_values": [],
            "flags": [],
        }
        for key, default in defaults.items():
            parsed.setdefault(key, default)

        # Coerce confidence
        try:
            parsed["confidence"] = float(parsed["confidence"])
            parsed["confidence"] = max(0.0, min(1.0, parsed["confidence"]))
        except (ValueError, TypeError):
            parsed["confidence"] = 0.0

        return parsed

    def _uncertainty_gate(self, response: dict) -> dict[str, Any]:
        """Apply the I-Don't-Know filter: low-confidence non-abstentions get gated."""
        if response.get("abstain"):
            return {"gated": False, "reason": "agent self-abstained"}
        if response.get("confidence", 0.0) < 0.4:
            return {
                "gated": True,
                "reason": f"Confidence {response.get('confidence', 0.0):.2f} below threshold 0.4; uncertainty gate triggered",
            }
        return {"gated": False, "reason": ""}
