"""
Reusable UI components for the LedgerMind Streamlit app.
"""

import streamlit as st


AGENT_METADATA = {
    "CA": {"name": "Compliance Advisor", "role": "US Tax & Regulatory Specialist"},
    "Analyst": {"name": "Financial Analyst", "role": "Spending & Cash Flow Specialist"},
    "Risk": {"name": "Risk Auditor", "role": "Anomaly & Fraud Detection Specialist"},
    "Investment": {"name": "Investment Advisor", "role": "Portfolio & Diversification Specialist"},
}


def render_agent_card(agent_key: str, response: dict) -> None:
    """Render a single specialist agent's response."""
    meta = AGENT_METADATA.get(agent_key, {"name": agent_key, "role": ""})
    abstained = response.get("abstain", False)
    card_class = "agent-card-abstain" if abstained else "agent-card"

    html = f'<div class="{card_class}">'
    html += f'<div class="agent-name">{meta["name"]}</div>'
    html += f'<div class="agent-role">{meta["role"]}</div>'

    if abstained:
        html += '<div class="verdict-text" style="font-style: italic; color: #6B7280;">'
        html += f'Abstained: {response.get("abstain_reason", "Out of scope for this specialist.")}'
        html += '</div>'
    else:
        verdict = response.get("verdict", "No verdict provided.")
        reasoning = response.get("reasoning", "")
        confidence = response.get("confidence", 0.0)

        html += f'<div class="verdict-text">{verdict}</div>'
        if reasoning:
            html += f'<div class="reasoning-text">{reasoning}</div>'

        # Confidence bar
        confidence_pct = int(confidence * 100)
        html += f'<div class="confidence-bar-container">'
        html += f'<span class="confidence-label">Confidence</span>'
        html += f'<span class="confidence-value">{confidence_pct}%</span>'
        html += f'</div>'

        # Flags
        flags = response.get("flags", [])
        if flags:
            html += '<div style="margin-top: 0.75rem;">'
            for flag in flags:
                html += f'<span class="flag-pill">{flag}</span>'
            html += '</div>'

        # Citations
        citations = response.get("citations", [])
        if citations:
            for cite in citations[:3]:
                source = cite.get("source", "")
                topic = cite.get("topic", "")
                if source or topic:
                    html += f'<div class="citation-block"><strong>{topic}</strong> &mdash; {source}</div>'

    # Latency footer
    meta_data = response.get("_meta", {})
    if meta_data:
        latency = meta_data.get("latency_ms", 0)
        html += f'<div style="margin-top: 0.75rem; font-size: 0.72rem; color: #9CA3AF; font-family: Inter, sans-serif;">'
        html += f'Response time: {latency:.0f}ms'
        html += f'</div>'

    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_consensus_summary(final_output: dict, consensus: dict) -> None:
    """Render the mediator's synthesized consensus output."""
    summary = final_output.get("summary", "")
    key_findings = final_output.get("key_findings", [])
    disagreements = final_output.get("disagreements", [])
    actions = final_output.get("recommended_actions", [])
    confidence = final_output.get("confidence", 0.0)
    abstained = final_output.get("agents_abstained", [])

    html = '<div class="summary-block">'
    html += '<h3>Consensus Summary</h3>'
    if summary:
        html += f'<p style="font-size: 1.0rem; line-height: 1.6;">{summary}</p>'

    if key_findings:
        html += '<h4 style="color: #FAF9F6 !important; margin-top: 1.25rem; font-size: 0.95rem;">Key Findings</h4>'
        html += '<ul style="margin-top: 0.5rem;">'
        for f in key_findings:
            html += f'<li style="margin-bottom: 0.4rem;">{f}</li>'
        html += '</ul>'

    if disagreements:
        html += '<h4 style="color: #FAF9F6 !important; margin-top: 1.25rem; font-size: 0.95rem;">Points of Disagreement</h4>'
        html += '<ul>'
        for d in disagreements:
            topic = d.get("topic", "")
            positions = d.get("positions", [])
            html += f'<li><strong>{topic}</strong><ul>'
            for p in positions:
                html += f'<li>{p.get("agent", "")}: {p.get("view", "")}</li>'
            html += '</ul></li>'
        html += '</ul>'

    if actions:
        html += '<h4 style="color: #FAF9F6 !important; margin-top: 1.25rem; font-size: 0.95rem;">Recommended Next Steps</h4>'
        html += '<ul>'
        for a in actions:
            html += f'<li style="margin-bottom: 0.4rem;">{a}</li>'
        html += '</ul>'

    html += f'<div style="margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid rgba(255,255,255,0.2); font-size: 0.85rem; color: #FAF9F6;">'
    html += f'<span style="color: #FAF9F6;">Aggregate confidence:</span> <strong style="color: #FFFFFF;">{int(confidence * 100)}%</strong> &nbsp;|&nbsp; '
    html += f'<span style="color: #FAF9F6;">Agents consulted:</span> <strong style="color: #FFFFFF;">{4 - len(abstained)}</strong> <span style="color: #FAF9F6;">of 4</span>'
    if abstained:
        html += f' &nbsp;|&nbsp; <span style="color: #FAF9F6;">Abstained:</span> <strong style="color: #FFFFFF;">{", ".join(abstained)}</strong>'
    html += '</div>'

    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_audit_panel(audit_summary: dict, session_events: list[dict]) -> None:
    """Render the audit log panel in the sidebar."""
    st.markdown("### Audit Trail")
    st.markdown(f"**Session ID:** `{audit_summary['session_id']}`")
    st.markdown(f"**Events logged:** {audit_summary['total_events']}")

    with st.expander("Event breakdown", expanded=False):
        for event_type, count in audit_summary["event_counts"].items():
            st.markdown(f"- {event_type}: {count}")

    with st.expander("Recent events (last 10)", expanded=False):
        for event in session_events[-10:]:
            event_type = event.get("event_type", "unknown")
            ts = event.get("timestamp", "")[:19]
            st.markdown(f"`{ts}` — **{event_type}**")