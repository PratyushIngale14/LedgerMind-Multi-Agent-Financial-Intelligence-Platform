"""
LedgerMind: Multi-Agent Personal CA System

A Streamlit application that orchestrates four specialist financial agents
(Compliance Advisor, Financial Analyst, Risk Auditor, Investment Advisor)
to answer user questions with traceable reasoning and explicit consensus.

Run:
    streamlit run app.py
"""

import json
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Load .env file for local development; skip silently on Streamlit Cloud (uses Secrets)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent))

from agents.orchestrator import Orchestrator
from tools.llm_client import LLMClient
from tools.rag_engine import MockRAGEngine
from ui.components import (
    render_agent_card,
    render_audit_panel,
    render_consensus_summary,
)
from ui.styles import CUSTOM_CSS
from utils.audit_log import AuditLogger
from utils.data_generator import save_all


# Page config
st.set_page_config(
    page_title="LedgerMind",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# Initialize session state
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None
if "audit_logger" not in st.session_state:
    st.session_state.audit_logger = None
if "financial_data" not in st.session_state:
    st.session_state.financial_data = None
if "history" not in st.session_state:
    st.session_state.history = []
if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False


@st.cache_resource
def initialize_system():
    """Create the orchestrator, RAG engine, audit logger, and load data."""
    sample_dir = Path("./sample_data")
    if not (sample_dir / "portfolio.json").exists():
        save_all(output_dir=str(sample_dir))

    # Load financial data
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

    financial_data = {
        "bank": bank,
        "credit_card": credit_card,
        "bills": bills,
        "loans": loans,
        "portfolio": portfolio,
        "income": income,
        "timeline": timeline,
    }

    llm = LLMClient()
    rag = MockRAGEngine(kb_path=str(Path("./knowledge_base/tax_and_compliance_kb.json")))
    audit = AuditLogger(log_dir=os.getenv("AUDIT_LOG_PATH", "./audit_logs"))
    orchestrator = Orchestrator(llm, rag, audit)

    return orchestrator, audit, financial_data


# Header
st.markdown(
    """
    <div style="margin-bottom: 1.5rem;">
        <h1 style="margin-bottom: 0.25rem;">LedgerMind</h1>
        <div style="font-family: 'Inter', sans-serif; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.12em; color: #6B7280;">
            Multi-Agent Personal Compliance & Advisory System
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.markdown("### About")
    st.markdown(
        """
        LedgerMind orchestrates four specialist financial agents that reason
        in parallel on every question, then reach explicit consensus.

        **Agents**
        - Compliance Advisor (CA)
        - Financial Analyst
        - Risk Auditor
        - Investment Advisor

        Each verdict is grounded in retrieved knowledge and deterministic
        calculations. Disagreements are surfaced rather than hidden.
        """
    )

    st.markdown("---")
    st.markdown("### Sample Questions")
    sample_questions = [
        "What's my 2025 Roth IRA contribution limit?",
        "How much did I spend on dining last month?",
        "Are there any duplicate or suspicious charges?",
        "Is my portfolio too concentrated in technology?",
        "Should I sell AAPL to fund my IRA this year?",
        "Give me a complete financial health review.",
    ]
    for q in sample_questions:
        if st.button(q, key=f"sample_{q[:20]}", use_container_width=True):
            st.session_state.pending_query = q

    st.markdown("---")
    if st.session_state.audit_logger:
        summary = st.session_state.audit_logger.get_session_summary()
        render_audit_panel(summary, st.session_state.audit_logger.events)


# Initialize system
api_key_present = bool(os.getenv("ANTHROPIC_API_KEY"))
mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"

if not api_key_present and not mock_mode:
    st.warning(
        "ANTHROPIC_API_KEY is not set. Either add it to a .env file in the "
        "project root, or set MOCK_MODE=true to run without API calls."
    )
    st.stop()

if not st.session_state.data_loaded:
    with st.spinner("Initializing agents and loading financial data..."):
        try:
            orchestrator, audit_logger, financial_data = initialize_system()
            st.session_state.orchestrator = orchestrator
            st.session_state.audit_logger = audit_logger
            st.session_state.financial_data = financial_data
            st.session_state.data_loaded = True
        except Exception as e:
            st.error(f"Failed to initialize system: {e}")
            st.stop()


# Financial snapshot summary
with st.expander("Financial Data Overview", expanded=False):
    col1, col2, col3 = st.columns(3)
    fd = st.session_state.financial_data
    with col1:
        st.markdown("**Portfolio**")
        st.metric("Total Value", f"${fd['portfolio']['total_account_value']:,.2f}")
        st.metric("Unrealized Gain", f"${fd['portfolio']['unrealized_gain']:,.2f}")
    with col2:
        st.markdown("**Income (YTD)**")
        st.metric("Gross Income", f"${fd['income']['ytd_gross_income']:,.2f}")
        st.metric("Federal Withholding", f"${fd['income']['ytd_federal_withholding']:,.2f}")
    with col3:
        st.markdown("**Debt**")
        total_debt = sum(loan["current_balance"] for loan in fd["loans"])
        total_monthly = sum(loan["monthly_payment"] for loan in fd["loans"])
        st.metric("Total Balance", f"${total_debt:,.2f}")
        st.metric("Monthly Payments", f"${total_monthly:,.2f}")


# Query input
st.markdown("### Ask LedgerMind")
default_query = st.session_state.pop("pending_query", "")
query = st.text_input(
    "Your question",
    value=default_query,
    placeholder="e.g. Is my portfolio properly diversified?",
    label_visibility="collapsed",
)

col_a, col_b = st.columns([1, 5])
with col_a:
    submit = st.button("Analyze", use_container_width=True)


# Run query
if submit and query.strip():
    with st.spinner("Four agents reasoning in parallel..."):
        try:
            result = st.session_state.orchestrator.run(
                user_query=query,
                financial_data=st.session_state.financial_data,
            )
            st.session_state.history.append({"query": query, "result": result})
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.stop()


# Display latest result
if st.session_state.history:
    latest = st.session_state.history[-1]
    result = latest["result"]

    st.markdown("---")
    st.markdown(f"**Question:** {latest['query']}")

    # Consensus summary first
    render_consensus_summary(result["final_output"], result["consensus"])

    # Individual agent responses
    st.markdown("### Specialist Agent Responses")
    col_left, col_right = st.columns(2)
    with col_left:
        render_agent_card("CA", result["ca_response"])
        render_agent_card("Risk", result["risk_response"])
    with col_right:
        render_agent_card("Analyst", result["analyst_response"])
        render_agent_card("Investment", result["investment_response"])

    # Consensus metrics
    with st.expander("Consensus & Audit Metrics", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Average Confidence", f"{result['consensus']['average_confidence']:.0%}")
        with c2:
            st.metric("Confidence Spread", f"{result['consensus']['confidence_spread']:.2f}")
        with c3:
            st.metric("Agents Abstained", f"{len(result['consensus']['agents_abstained'])}/4")

        st.json(result["consensus"])


# Footer
st.markdown(
    """
    <div style="margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #D4CFC2;
                font-size: 0.75rem; color: #9CA3AF; font-family: 'Inter', sans-serif;">
        LedgerMind is an educational demonstration of multi-agent financial reasoning.
        Outputs are informational only and do not constitute tax, investment, or legal advice.
    </div>
    """,
    unsafe_allow_html=True,
)