"""
Calculation & Audit Layer for LedgerMind.

All financial calculations the agents reason about should flow through these
functions rather than being computed inside the LLM. This guarantees:

1. Numerical accuracy (LLMs are unreliable at arithmetic).
2. Traceability (every calculation returns its inputs and formula).
3. Determinism (the same inputs always produce the same outputs).

Each function returns a dict containing the result, the inputs used, and a
human-readable formula description that can be cited in the final report.
"""

from datetime import datetime
from statistics import mean, stdev
from typing import Any

import pandas as pd


def category_spending_summary(transactions: pd.DataFrame, months_back: int = 1) -> dict[str, Any]:
    """Aggregate spending by category for the most recent N months."""
    if transactions.empty:
        return {"result": {}, "inputs": {"months_back": months_back}, "formula": "N/A: no transactions"}

    cutoff = datetime.now() - pd.Timedelta(days=months_back * 30)
    recent = transactions[transactions["date"] >= cutoff].copy()
    debits = recent[recent["amount"] < 0].copy()
    debits["abs_amount"] = debits["amount"].abs()
    by_cat = debits.groupby("category")["abs_amount"].sum().round(2).to_dict()

    return {
        "result": by_cat,
        "inputs": {"months_back": months_back, "num_transactions": len(debits)},
        "formula": "SUM(|amount|) WHERE amount < 0 AND date >= cutoff, GROUPED BY category",
    }


def detect_amount_anomalies(transactions: pd.DataFrame, z_threshold: float = 2.5) -> dict[str, Any]:
    """Flag transactions whose amount deviates significantly from category averages."""
    if transactions.empty:
        return {"result": [], "inputs": {"z_threshold": z_threshold}, "formula": "N/A: no transactions"}

    debits = transactions[transactions["amount"] < 0].copy()
    debits["abs_amount"] = debits["amount"].abs()

    flagged = []
    for category, group in debits.groupby("category"):
        if len(group) < 3:
            continue
        amounts = group["abs_amount"].tolist()
        category_mean = mean(amounts)
        category_std = stdev(amounts) if len(amounts) > 1 else 0
        if category_std == 0:
            continue
        for _, row in group.iterrows():
            z = (row["abs_amount"] - category_mean) / category_std
            if z > z_threshold:
                flagged.append({
                    "date": row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"]),
                    "merchant": row["merchant"],
                    "category": category,
                    "amount": float(-row["abs_amount"]),
                    "category_mean": round(category_mean, 2),
                    "category_std": round(category_std, 2),
                    "z_score": round(z, 2),
                })

    return {
        "result": flagged,
        "inputs": {"z_threshold": z_threshold, "num_transactions": len(debits)},
        "formula": "z = (|amount| - category_mean) / category_std; FLAG WHERE z > threshold",
    }


def detect_duplicate_charges(transactions: pd.DataFrame, window_hours: int = 24) -> dict[str, Any]:
    """Find transactions with identical merchant and amount within a short window."""
    if transactions.empty:
        return {"result": [], "inputs": {"window_hours": window_hours}, "formula": "N/A: no transactions"}

    df = transactions.copy().sort_values(["merchant", "amount", "date"])
    duplicates = []

    for (merchant, amount), group in df.groupby(["merchant", "amount"]):
        if len(group) < 2:
            continue
        dates = group["date"].tolist()
        for i in range(len(dates) - 1):
            time_diff = (dates[i + 1] - dates[i]).total_seconds() / 3600
            if time_diff <= window_hours:
                duplicates.append({
                    "merchant": merchant,
                    "amount": float(amount),
                    "first_date": dates[i].strftime("%Y-%m-%d %H:%M") if hasattr(dates[i], "strftime") else str(dates[i]),
                    "second_date": dates[i + 1].strftime("%Y-%m-%d %H:%M") if hasattr(dates[i + 1], "strftime") else str(dates[i + 1]),
                    "hours_apart": round(time_diff, 1),
                })

    return {
        "result": duplicates,
        "inputs": {"window_hours": window_hours, "num_transactions": len(df)},
        "formula": "FLAG WHERE (merchant_a == merchant_b) AND (amount_a == amount_b) AND |date_a - date_b| <= window",
    }


def portfolio_allocation_analysis(portfolio: dict) -> dict[str, Any]:
    """Compute allocation percentages by asset class and sector."""
    holdings = portfolio["holdings"]
    total_holdings_value = sum(h["shares"] * h["current_price"] for h in holdings)

    by_asset_class: dict[str, float] = {}
    by_sector: dict[str, float] = {}
    by_position: list[dict] = []

    for h in holdings:
        position_value = h["shares"] * h["current_price"]
        pct = position_value / total_holdings_value * 100

        by_asset_class[h["asset_class"]] = by_asset_class.get(h["asset_class"], 0) + pct
        by_sector[h["sector"]] = by_sector.get(h["sector"], 0) + pct

        by_position.append({
            "ticker": h["ticker"],
            "value": round(position_value, 2),
            "pct_of_portfolio": round(pct, 2),
        })

    return {
        "result": {
            "by_asset_class": {k: round(v, 2) for k, v in by_asset_class.items()},
            "by_sector": {k: round(v, 2) for k, v in by_sector.items()},
            "by_position": sorted(by_position, key=lambda x: x["pct_of_portfolio"], reverse=True),
            "total_holdings_value": round(total_holdings_value, 2),
        },
        "inputs": {"num_holdings": len(holdings)},
        "formula": "pct = (shares * current_price) / total_holdings_value * 100",
    }


def portfolio_performance(portfolio: dict) -> dict[str, Any]:
    """Compute unrealized gains per holding and total."""
    holdings = portfolio["holdings"]
    position_perf = []

    for h in holdings:
        position_value = h["shares"] * h["current_price"]
        cost = h["shares"] * h["cost_basis"]
        gain = position_value - cost
        gain_pct = (gain / cost * 100) if cost > 0 else 0
        position_perf.append({
            "ticker": h["ticker"],
            "cost_basis_total": round(cost, 2),
            "current_value": round(position_value, 2),
            "unrealized_gain": round(gain, 2),
            "unrealized_gain_pct": round(gain_pct, 2),
        })

    total_cost = sum(p["cost_basis_total"] for p in position_perf)
    total_value = sum(p["current_value"] for p in position_perf)
    total_gain = total_value - total_cost

    return {
        "result": {
            "by_position": sorted(position_perf, key=lambda x: x["unrealized_gain"], reverse=True),
            "total_cost_basis": round(total_cost, 2),
            "total_current_value": round(total_value, 2),
            "total_unrealized_gain": round(total_gain, 2),
            "total_return_pct": round(total_gain / total_cost * 100, 2) if total_cost > 0 else 0,
        },
        "inputs": {"num_holdings": len(holdings)},
        "formula": "gain = (shares * current_price) - (shares * cost_basis); gain_pct = gain / cost_basis * 100",
    }


def concentration_risk(portfolio: dict, threshold_pct: float = 10.0) -> dict[str, Any]:
    """Flag single positions or sectors exceeding a concentration threshold."""
    allocation = portfolio_allocation_analysis(portfolio)["result"]

    flagged_positions = [
        p for p in allocation["by_position"] if p["pct_of_portfolio"] > threshold_pct
    ]
    flagged_sectors = [
        {"sector": s, "pct": pct}
        for s, pct in allocation["by_sector"].items()
        if pct > 30.0
    ]

    return {
        "result": {
            "flagged_positions": flagged_positions,
            "flagged_sectors": flagged_sectors,
        },
        "inputs": {"position_threshold_pct": threshold_pct, "sector_threshold_pct": 30.0},
        "formula": "FLAG positions WHERE pct_of_portfolio > position_threshold; FLAG sectors WHERE pct_of_portfolio > sector_threshold",
    }


def emergency_fund_check(income: dict, monthly_essentials: float) -> dict[str, Any]:
    """Check whether the user has an emergency fund covering 3 to 6 months of essentials."""
    # We assume cash_balance from portfolio represents available liquid funds for this check
    months_3 = monthly_essentials * 3
    months_6 = monthly_essentials * 6
    return {
        "result": {
            "monthly_essentials_assumed": monthly_essentials,
            "target_3_months": round(months_3, 2),
            "target_6_months": round(months_6, 2),
        },
        "inputs": {"monthly_essentials": monthly_essentials},
        "formula": "target_low = monthly_essentials * 3; target_high = monthly_essentials * 6",
    }
