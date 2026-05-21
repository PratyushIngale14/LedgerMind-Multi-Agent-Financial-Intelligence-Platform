"""
The four specialist agents in LedgerMind.

Each agent inherits from SpecialistAgent and customizes:
1. Which slices of the financial data it pulls into context.
2. What it searches for in the knowledge base.
3. Which precomputed calculations it relies on.
"""

import json
from typing import Any

import pandas as pd

from agents.base_agent import SpecialistAgent
from agents.prompts import (
    ANALYST_AGENT_PROMPT,
    CA_AGENT_PROMPT,
    INVESTMENT_AGENT_PROMPT,
    RISK_AGENT_PROMPT,
)
from tools import calculations


class CAAgent(SpecialistAgent):
    """Compliance Advisor agent. Focuses on US tax and regulatory matters."""

    name = "CA"
    system_prompt = CA_AGENT_PROMPT

    def build_rag_query(self, query: str) -> str:
        return f"tax compliance IRS retirement contribution {query}"

    def build_context(self, query: str, financial_data: dict) -> dict[str, Any]:
        ctx = {}
        if "income" in financial_data:
            ctx["Income Summary"] = json.dumps(financial_data["income"], indent=2)
        if "portfolio" in financial_data:
            portfolio = financial_data["portfolio"]
            ctx["Retirement Accounts"] = json.dumps(portfolio.get("retirement_accounts", {}), indent=2)
            ctx["Taxable Brokerage Summary"] = json.dumps({
                "total_value": portfolio.get("total_account_value"),
                "unrealized_gain": portfolio.get("unrealized_gain"),
                "cash_balance": portfolio.get("cash_balance"),
            }, indent=2)
        if "loans" in financial_data:
            ctx["Active Loans"] = json.dumps(financial_data["loans"], indent=2)
        return ctx


class AnalystAgent(SpecialistAgent):
    """Financial Analyst agent. Focuses on spending patterns and cash flow."""

    name = "Analyst"
    system_prompt = ANALYST_AGENT_PROMPT

    def build_rag_query(self, query: str) -> str:
        return f"budget spending emergency fund {query}"

    def build_context(self, query: str, financial_data: dict) -> dict[str, Any]:
        ctx = {}
        if "credit_card" in financial_data:
            cc: pd.DataFrame = financial_data["credit_card"]
            summary = calculations.category_spending_summary(cc, months_back=1)
            ctx["Last Month Spending by Category (USD)"] = json.dumps(summary["result"], indent=2)
            ctx["Calculation Formula"] = summary["formula"]

            summary_3mo = calculations.category_spending_summary(cc, months_back=3)
            ctx["Three Month Spending by Category (USD)"] = json.dumps(summary_3mo["result"], indent=2)
        if "income" in financial_data:
            ctx["Income Summary"] = json.dumps(financial_data["income"], indent=2)
        if "bills" in financial_data:
            ctx["Recurring Bills"] = json.dumps(financial_data["bills"], indent=2)
        if "loans" in financial_data:
            total_emi = sum(loan["monthly_payment"] for loan in financial_data["loans"])
            ctx["Total Monthly Loan Payments"] = f"${total_emi:.2f}"
        return ctx


class RiskAgent(SpecialistAgent):
    """Risk Auditor agent. Focuses on anomalies and red flags."""

    name = "Risk"
    system_prompt = RISK_AGENT_PROMPT

    def build_rag_query(self, query: str) -> str:
        return f"anomaly fraud duplicate suspicious {query}"

    def build_context(self, query: str, financial_data: dict) -> dict[str, Any]:
        ctx = {}
        if "credit_card" in financial_data:
            cc: pd.DataFrame = financial_data["credit_card"]
            anomalies = calculations.detect_amount_anomalies(cc, z_threshold=2.5)
            ctx["Amount Anomalies (z-score > 2.5)"] = json.dumps(anomalies["result"], indent=2, default=str)
            ctx["Anomaly Formula"] = anomalies["formula"]

            duplicates = calculations.detect_duplicate_charges(cc, window_hours=24)
            ctx["Duplicate Charge Candidates"] = json.dumps(duplicates["result"], indent=2, default=str)
            ctx["Duplicate Formula"] = duplicates["formula"]
        if "portfolio" in financial_data:
            risk = calculations.concentration_risk(financial_data["portfolio"], threshold_pct=10.0)
            ctx["Concentration Risk Flags"] = json.dumps(risk["result"], indent=2)
        return ctx


class InvestmentAgent(SpecialistAgent):
    """Investment Advisor agent. Focuses on portfolio composition and diversification."""

    name = "Investment"
    system_prompt = INVESTMENT_AGENT_PROMPT

    def build_rag_query(self, query: str) -> str:
        return f"diversification allocation portfolio expense ratio {query}"

    def build_context(self, query: str, financial_data: dict) -> dict[str, Any]:
        ctx = {}
        if "portfolio" in financial_data:
            portfolio = financial_data["portfolio"]
            allocation = calculations.portfolio_allocation_analysis(portfolio)
            ctx["Allocation Analysis"] = json.dumps(allocation["result"], indent=2)
            ctx["Allocation Formula"] = allocation["formula"]

            perf = calculations.portfolio_performance(portfolio)
            ctx["Performance Analysis"] = json.dumps(perf["result"], indent=2)

            ctx["Account Summary"] = json.dumps({
                "total_value": portfolio.get("total_account_value"),
                "cash_balance": portfolio.get("cash_balance"),
                "retirement_accounts": portfolio.get("retirement_accounts"),
            }, indent=2)
        return ctx
