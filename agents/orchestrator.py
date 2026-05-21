"""
LangGraph orchestrator for LedgerMind.

Implements the architecture from the design diagram:

    USER QUERY
        |
        v
    [Parallel: 4 specialist agents each retrieve from RAG, run their tools,
    and produce a structured verdict with confidence and citations]
        |
        v
    [Disagreement & Consensus Handler: compares verdicts, identifies
    agreements and disagreements]
        |
        v
    [Uncertainty Gate: filters out low-confidence responses already gated
    at the agent level]
        |
        v
    [Consensus Logic & Mediator: LLM call that synthesizes the responses
    into a single user-facing answer, preserving disagreements]
        |
        v
    AUDIT-READY OUTPUT
"""

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from agents.prompts import MEDIATOR_PROMPT
from agents.specialists import (
    AnalystAgent,
    CAAgent,
    InvestmentAgent,
    RiskAgent,
)
from tools.llm_client import LLMClient
from tools.rag_engine import MockRAGEngine
from utils.audit_log import AuditLogger


class LedgerMindState(TypedDict):
    """State passed between nodes in the orchestration graph."""
    user_query: str
    financial_data: dict
    ca_response: dict
    analyst_response: dict
    risk_response: dict
    investment_response: dict
    consensus: dict
    final_output: dict


class Orchestrator:
    """LangGraph-based multi-agent orchestrator."""

    def __init__(self, llm: LLMClient, rag: MockRAGEngine, audit: AuditLogger):
        self.llm = llm
        self.rag = rag
        self.audit = audit

        self.ca_agent = CAAgent(llm, rag, audit)
        self.analyst_agent = AnalystAgent(llm, rag, audit)
        self.risk_agent = RiskAgent(llm, rag, audit)
        self.investment_agent = InvestmentAgent(llm, rag, audit)

        self.graph = self._build_graph()

    def _build_graph(self):
        """Construct the LangGraph state machine."""
        graph = StateGraph(LedgerMindState)

        graph.add_node("run_agents", self._run_agents_node)
        graph.add_node("compute_consensus", self._consensus_node)
        graph.add_node("finalize", self._finalize_node)

        graph.add_edge(START, "run_agents")
        graph.add_edge("run_agents", "compute_consensus")
        graph.add_edge("compute_consensus", "finalize")
        graph.add_edge("finalize", END)

        return graph.compile()

    def _run_agents_node(self, state: LedgerMindState) -> dict:
        """Run all four specialist agents in parallel."""
        query = state["user_query"]
        data = state["financial_data"]

        agents = {
            "ca_response": (self.ca_agent, query, data),
            "analyst_response": (self.analyst_agent, query, data),
            "risk_response": (self.risk_agent, query, data),
            "investment_response": (self.investment_agent, query, data),
        }

        results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_key = {
                executor.submit(agent.respond, q, d): key
                for key, (agent, q, d) in agents.items()
            }
            for future in future_to_key:
                key = future_to_key[future]
                try:
                    results[key] = future.result()
                except Exception as e:
                    results[key] = {
                        "verdict": "Agent failed to respond",
                        "confidence": 0.0,
                        "abstain": True,
                        "abstain_reason": f"Agent execution error: {str(e)[:200]}",
                        "reasoning": "",
                        "citations": [],
                        "computed_values": [],
                        "flags": ["agent_error"],
                        "_meta": {"error": str(e)[:200]},
                    }
        return results

    def _consensus_node(self, state: LedgerMindState) -> dict:
        """Compute agreement and disagreement metrics."""
        agents = {
            "CA": state["ca_response"],
            "Analyst": state["analyst_response"],
            "Risk": state["risk_response"],
            "Investment": state["investment_response"],
        }

        abstained = [name for name, resp in agents.items() if resp.get("abstain")]
        responding = [name for name, resp in agents.items() if not resp.get("abstain")]

        # Aggregate flags across agents to detect disagreements
        all_flags = {}
        for name, resp in agents.items():
            if not resp.get("abstain"):
                for flag in resp.get("flags", []):
                    all_flags.setdefault(flag, []).append(name)

        # A naive disagreement detector: significant confidence spread
        confidences = [resp.get("confidence", 0.0) for name, resp in agents.items() if not resp.get("abstain")]
        confidence_spread = (max(confidences) - min(confidences)) if confidences else 0.0
        likely_disagreement = confidence_spread > 0.4

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        consensus = {
            "agents_responding": responding,
            "agents_abstained": abstained,
            "average_confidence": round(avg_confidence, 2),
            "confidence_spread": round(confidence_spread, 2),
            "likely_disagreement": likely_disagreement,
            "shared_flags": {flag: agents_list for flag, agents_list in all_flags.items() if len(agents_list) >= 2},
        }

        self.audit.log_consensus(
            agreement=not likely_disagreement,
            agents_agreed=responding,
            agents_disagreed=[],
            final_verdict="pending_mediator",
        )

        return {"consensus": consensus}

    def _finalize_node(self, state: LedgerMindState) -> dict:
        """Call the Mediator LLM to synthesize the final response."""
        agents_payload = {
            "CA": {
                "verdict": state["ca_response"].get("verdict", ""),
                "abstain": state["ca_response"].get("abstain", False),
                "confidence": state["ca_response"].get("confidence", 0.0),
                "reasoning": state["ca_response"].get("reasoning", ""),
                "citations": state["ca_response"].get("citations", []),
                "flags": state["ca_response"].get("flags", []),
            },
            "Analyst": {
                "verdict": state["analyst_response"].get("verdict", ""),
                "abstain": state["analyst_response"].get("abstain", False),
                "confidence": state["analyst_response"].get("confidence", 0.0),
                "reasoning": state["analyst_response"].get("reasoning", ""),
                "citations": state["analyst_response"].get("citations", []),
                "flags": state["analyst_response"].get("flags", []),
            },
            "Risk": {
                "verdict": state["risk_response"].get("verdict", ""),
                "abstain": state["risk_response"].get("abstain", False),
                "confidence": state["risk_response"].get("confidence", 0.0),
                "reasoning": state["risk_response"].get("reasoning", ""),
                "citations": state["risk_response"].get("citations", []),
                "flags": state["risk_response"].get("flags", []),
            },
            "Investment": {
                "verdict": state["investment_response"].get("verdict", ""),
                "abstain": state["investment_response"].get("abstain", False),
                "confidence": state["investment_response"].get("confidence", 0.0),
                "reasoning": state["investment_response"].get("reasoning", ""),
                "citations": state["investment_response"].get("citations", []),
                "flags": state["investment_response"].get("flags", []),
            },
        }

        import json
        user_message = (
            f"USER QUESTION:\n{state['user_query']}\n\n"
            f"AGENT RESPONSES:\n{json.dumps(agents_payload, indent=2)}\n\n"
            f"CONSENSUS METRICS:\n{json.dumps(state['consensus'], indent=2)}\n\n"
            f"Synthesize the agent responses into a single answer per your output schema."
        )

        start = time.time()
        mediator_response = self.llm.complete_json(
            system_prompt=MEDIATOR_PROMPT,
            user_message=user_message,
            max_tokens=2000,
        )
        latency_ms = (time.time() - start) * 1000

        final = mediator_response.get("parsed", {})
        if final.get("parse_error"):
            final = self._fallback_synthesis(state, agents_payload)

        # Aggregate citations across agents
        all_citations = []
        seen = set()
        for agent_data in agents_payload.values():
            for cite in agent_data.get("citations", []):
                key = (cite.get("source", ""), cite.get("topic", ""))
                if key not in seen and key != ("", ""):
                    all_citations.append(cite)
                    seen.add(key)
        final.setdefault("citations", all_citations)

        final["_meta"] = {
            "mediator_latency_ms": round(latency_ms, 1),
            "mediator_tokens": mediator_response.get("usage"),
        }

        self.audit.log_final_output({
            "consensus_reached": not state["consensus"]["likely_disagreement"],
            "num_agents_responded": len(state["consensus"]["agents_responding"]),
            "num_agents_abstained": len(state["consensus"]["agents_abstained"]),
        })

        return {"final_output": final}

    def _fallback_synthesis(self, state: LedgerMindState, agents_payload: dict) -> dict:
        """If the mediator fails to return JSON, build a structured response manually."""
        non_abstain = [a for a, d in agents_payload.items() if not d["abstain"]]
        return {
            "summary": "Multiple specialist agents reviewed this question. See the individual agent responses below.",
            "key_findings": [
                f"{name}: {data['verdict']}"
                for name, data in agents_payload.items()
                if not data["abstain"]
            ],
            "disagreements": [],
            "recommended_actions": [],
            "citations": [],
            "confidence": state["consensus"]["average_confidence"],
            "agents_consulted": non_abstain,
            "agents_abstained": [a for a, d in agents_payload.items() if d["abstain"]],
        }

    def run(self, user_query: str, financial_data: dict) -> dict:
        """Execute the full pipeline for a user query."""
        self.audit.log_user_query(user_query)

        initial_state = {
            "user_query": user_query,
            "financial_data": financial_data,
            "ca_response": {},
            "analyst_response": {},
            "risk_response": {},
            "investment_response": {},
            "consensus": {},
            "final_output": {},
        }

        result = self.graph.invoke(initial_state)
        return result