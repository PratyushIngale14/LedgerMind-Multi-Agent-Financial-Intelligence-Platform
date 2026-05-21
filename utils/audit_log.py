"""
Audit logging for LedgerMind.

Every agent decision, tool call, retrieval, and consensus event is logged
with a timestamp and the inputs/outputs that produced it. This is the
auditability layer of the system. Designed so that any final answer the
system gives can be reconstructed from the log alone.

Logs are written in JSON Lines (jsonl) format, one event per line, which
makes them trivial to parse with pandas or grep.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


class AuditLogger:
    """Append-only audit logger for a single session."""

    def __init__(self, log_dir: str = "./audit_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = str(uuid.uuid4())[:8]
        self.session_start = datetime.now()
        self.log_file = (
            self.log_dir
            / f"session_{self.session_start.strftime('%Y%m%d_%H%M%S')}_{self.session_id}.jsonl"
        )
        self.events: list[dict] = []

        self._write({
            "event_type": "session_start",
            "session_id": self.session_id,
            "timestamp": self.session_start.isoformat(),
        })

    def _write(self, event: dict) -> None:
        event.setdefault("timestamp", datetime.now().isoformat())
        event.setdefault("session_id", self.session_id)
        self.events.append(event)
        with open(self.log_file, "a") as f:
            f.write(json.dumps(event, default=str) + "\n")

    def log_user_query(self, query: str) -> None:
        self._write({"event_type": "user_query", "query": query})

    def log_rag_retrieval(self, agent: str, query: str, results: list[dict]) -> None:
        self._write({
            "event_type": "rag_retrieval",
            "agent": agent,
            "query": query,
            "num_results": len(results),
            "results": [{"topic": r.get("topic"), "source": r.get("source"), "authority_tier": r.get("authority_tier")} for r in results],
        })

    def log_tool_call(self, agent: str, tool_name: str, inputs: dict, outputs: Any) -> None:
        self._write({
            "event_type": "tool_call",
            "agent": agent,
            "tool_name": tool_name,
            "inputs": inputs,
            "outputs": outputs,
        })

    def log_agent_response(self, agent: str, response: dict, latency_ms: float) -> None:
        self._write({
            "event_type": "agent_response",
            "agent": agent,
            "verdict": response.get("verdict"),
            "confidence": response.get("confidence"),
            "abstained": response.get("abstain", False),
            "reasoning": response.get("reasoning"),
            "citations": response.get("citations", []),
            "latency_ms": latency_ms,
        })

    def log_consensus(self, agreement: bool, agents_agreed: list[str], agents_disagreed: list[str], final_verdict: str) -> None:
        self._write({
            "event_type": "consensus",
            "agreement_reached": agreement,
            "agents_agreed": agents_agreed,
            "agents_disagreed": agents_disagreed,
            "final_verdict": final_verdict,
        })

    def log_uncertainty_gate(self, agent: str, gated: bool, reason: str) -> None:
        self._write({
            "event_type": "uncertainty_gate",
            "agent": agent,
            "gated": gated,
            "reason": reason,
        })

    def log_calculation(self, description: str, inputs: dict, formula: str, result: Any) -> None:
        self._write({
            "event_type": "calculation",
            "description": description,
            "inputs": inputs,
            "formula": formula,
            "result": result,
        })

    def log_final_output(self, output: dict) -> None:
        self._write({
            "event_type": "final_output",
            "output_summary": {
                "consensus_reached": output.get("consensus_reached"),
                "num_agents_responded": output.get("num_agents_responded"),
                "num_agents_abstained": output.get("num_agents_abstained"),
            },
        })

    def get_session_summary(self) -> dict:
        """Summary statistics for the current session."""
        event_counts: dict[str, int] = {}
        for e in self.events:
            event_counts[e["event_type"]] = event_counts.get(e["event_type"], 0) + 1
        return {
            "session_id": self.session_id,
            "start_time": self.session_start.isoformat(),
            "duration_seconds": (datetime.now() - self.session_start).total_seconds(),
            "total_events": len(self.events),
            "event_counts": event_counts,
            "log_file": str(self.log_file),
        }
