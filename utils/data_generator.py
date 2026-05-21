"""
Synthetic data generator for LedgerMind.

Generates realistic US-context financial data across all eight source types
in the architecture: bank transactions, credit card data, bills, loans/EMIs,
investment portfolio, income records, and event timeline.

All data is fictional. No real account information is used.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
np.random.seed(42)
random.seed(42)


SPENDING_CATEGORIES = {
    "Groceries": ["Whole Foods", "Trader Joe's", "Kroger", "Walmart", "H-E-B"],
    "Dining": ["Chipotle", "Starbucks", "Local Diner", "DoorDash", "Uber Eats"],
    "Transportation": ["Shell", "Chevron", "Uber", "Lyft"],
    "Subscriptions": ["Netflix", "Spotify", "Adobe Creative Cloud", "iCloud Plus"],
    "Utilities": ["AT&T", "TXU Energy", "Arlington Water Utilities", "Verizon"],
    "Healthcare": ["CVS Pharmacy", "Walgreens", "Dental Clinic"],
    "Shopping": ["Amazon", "Target", "Best Buy", "Apple Store"],
    "Entertainment": ["AMC Theaters", "Spotify Concerts"],
    "Travel": ["Delta Airlines", "Marriott", "Airbnb"],
}

CATEGORY_AMOUNTS = {
    "Groceries": (15, 300, 85, 40),
    "Dining": (8, 120, 25, 15),
    "Transportation": (10, 90, 40, 20),
    "Subscriptions": (5, 50, 15, 8),
    "Utilities": (40, 250, 120, 40),
    "Healthcare": (15, 400, 60, 50),
    "Shopping": (20, 800, 90, 80),
    "Entertainment": (15, 200, 50, 30),
    "Travel": (100, 1500, 400, 300),
}


def generate_bank_transactions(num_months: int = 6) -> pd.DataFrame:
    """Generate checking account transactions."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=num_months * 30)
    transactions = []

    current = start_date
    while current <= end_date:
        # Bi-monthly payroll deposits
        if current.day in [1, 15]:
            transactions.append({
                "date": current,
                "merchant": "Employer Inc. Payroll",
                "category": "Income",
                "amount": 4200.00,
                "type": "credit",
                "account": "Checking",
            })

        # Monthly rent
        if current.day == 1:
            transactions.append({
                "date": current,
                "merchant": "Lakeview Property Management",
                "category": "Rent",
                "amount": -1800.00,
                "type": "debit",
                "account": "Checking",
            })

        # Auto-pay utilities
        if current.day == 8:
            transactions.append({
                "date": current,
                "merchant": "TXU Energy",
                "category": "Utilities",
                "amount": -round(random.uniform(80, 180), 2),
                "type": "debit",
                "account": "Checking",
            })

        current += timedelta(days=1)

    df = pd.DataFrame(transactions).sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    return df


def generate_credit_card_transactions(num_months: int = 6, plant_anomalies: bool = True) -> pd.DataFrame:
    """Generate credit card transactions with optional planted anomalies."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=num_months * 30)
    transactions = []

    # Monthly subscriptions on credit card
    current = start_date
    while current <= end_date:
        if current.day == 5:
            for sub in ["Netflix", "Spotify", "Adobe Creative Cloud"]:
                transactions.append({
                    "date": current,
                    "merchant": sub,
                    "category": "Subscriptions",
                    "amount": -round(random.uniform(10, 25), 2),
                    "type": "debit",
                    "account": "Credit Card",
                })
        current += timedelta(days=1)

    # Variable daily spending
    current = start_date
    while current <= end_date:
        num_today = np.random.poisson(1.5)
        for _ in range(num_today):
            category = random.choice([c for c in SPENDING_CATEGORIES.keys()
                                       if c not in ["Subscriptions", "Utilities"]])
            merchant = random.choice(SPENDING_CATEGORIES[category])
            min_amt, max_amt, mean, std = CATEGORY_AMOUNTS[category]
            amount = max(min_amt, min(max_amt, np.random.normal(mean, std)))
            transactions.append({
                "date": current,
                "merchant": merchant,
                "category": category,
                "amount": -round(amount, 2),
                "type": "debit",
                "account": "Credit Card",
            })
        current += timedelta(days=1)

    if plant_anomalies:
        recent = end_date - timedelta(days=12)

        # Anomaly 1: Unusually large dining charge
        transactions.append({
            "date": recent,
            "merchant": "Capital Grille Steakhouse",
            "category": "Dining",
            "amount": -487.50,
            "type": "debit",
            "account": "Credit Card",
        })

        # Anomaly 2: Duplicate subscription charge same day
        transactions.append({
            "date": recent + timedelta(days=2),
            "merchant": "Netflix",
            "category": "Subscriptions",
            "amount": -15.99,
            "type": "debit",
            "account": "Credit Card",
        })
        transactions.append({
            "date": recent + timedelta(days=2),
            "merchant": "Netflix",
            "category": "Subscriptions",
            "amount": -15.99,
            "type": "debit",
            "account": "Credit Card",
        })

        # Anomaly 3: Suspicious round-number charge from unknown merchant
        transactions.append({
            "date": recent + timedelta(days=5),
            "merchant": "Unknown Online Vendor",
            "category": "Shopping",
            "amount": -1000.00,
            "type": "debit",
            "account": "Credit Card",
        })

    df = pd.DataFrame(transactions).sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    return df


def generate_bills_and_utilities() -> list[dict]:
    """Recurring bills and utility commitments."""
    return [
        {"provider": "TXU Energy", "category": "Electricity", "avg_monthly": 135.00, "due_day": 8, "auto_pay": True},
        {"provider": "Arlington Water Utilities", "category": "Water", "avg_monthly": 65.00, "due_day": 15, "auto_pay": True},
        {"provider": "AT&T Fiber", "category": "Internet", "avg_monthly": 80.00, "due_day": 20, "auto_pay": True},
        {"provider": "Verizon Wireless", "category": "Mobile", "avg_monthly": 95.00, "due_day": 22, "auto_pay": True},
        {"provider": "Lakeview Property Management", "category": "Rent", "avg_monthly": 1800.00, "due_day": 1, "auto_pay": False},
        {"provider": "Geico", "category": "Auto Insurance", "avg_monthly": 145.00, "due_day": 10, "auto_pay": True},
    ]


def generate_loans_and_emis() -> list[dict]:
    """Active loan obligations."""
    return [
        {
            "loan_type": "Student Loan",
            "lender": "Federal Direct",
            "original_principal": 45000.00,
            "current_balance": 38200.00,
            "interest_rate": 5.50,
            "monthly_payment": 425.00,
            "remaining_months": 108,
            "status": "Active",
        },
        {
            "loan_type": "Auto Loan",
            "lender": "Toyota Financial",
            "original_principal": 28000.00,
            "current_balance": 18500.00,
            "interest_rate": 4.25,
            "monthly_payment": 510.00,
            "remaining_months": 38,
            "status": "Active",
        },
    ]


def generate_portfolio() -> dict:
    """Synthetic investment portfolio (taxable brokerage)."""
    holdings = [
        {"ticker": "AAPL", "name": "Apple Inc.", "shares": 35, "cost_basis": 145.20, "current_price": 226.50, "sector": "Technology", "asset_class": "US Large Cap"},
        {"ticker": "MSFT", "name": "Microsoft Corp.", "shares": 18, "cost_basis": 280.00, "current_price": 421.30, "sector": "Technology", "asset_class": "US Large Cap"},
        {"ticker": "GOOGL", "name": "Alphabet Inc.", "shares": 22, "cost_basis": 132.50, "current_price": 178.40, "sector": "Technology", "asset_class": "US Large Cap"},
        {"ticker": "NVDA", "name": "NVIDIA Corp.", "shares": 12, "cost_basis": 280.00, "current_price": 138.20, "sector": "Technology", "asset_class": "US Large Cap"},
        {"ticker": "VOO", "name": "Vanguard S&P 500 ETF", "shares": 25, "cost_basis": 380.00, "current_price": 512.80, "sector": "Diversified", "asset_class": "US Large Cap ETF"},
        {"ticker": "VTI", "name": "Vanguard Total Stock Market ETF", "shares": 18, "cost_basis": 215.00, "current_price": 278.40, "sector": "Diversified", "asset_class": "US Total Market ETF"},
        {"ticker": "QQQ", "name": "Invesco QQQ Trust", "shares": 15, "cost_basis": 320.00, "current_price": 478.20, "sector": "Technology", "asset_class": "US Large Cap ETF"},
        {"ticker": "VXUS", "name": "Vanguard Total International Stock", "shares": 30, "cost_basis": 52.00, "current_price": 61.80, "sector": "Diversified", "asset_class": "International ETF"},
        {"ticker": "BND", "name": "Vanguard Total Bond Market", "shares": 12, "cost_basis": 78.00, "current_price": 72.50, "sector": "Bonds", "asset_class": "Bond ETF"},
        {"ticker": "COIN", "name": "Coinbase Global", "shares": 8, "cost_basis": 195.00, "current_price": 245.80, "sector": "Financial Services", "asset_class": "Crypto-Related"},
    ]

    total_value = sum(h["shares"] * h["current_price"] for h in holdings)
    total_cost = sum(h["shares"] * h["cost_basis"] for h in holdings)

    return {
        "account_type": "Taxable Brokerage",
        "as_of_date": datetime.now().strftime("%Y-%m-%d"),
        "cash_balance": 8500.00,
        "holdings": holdings,
        "total_holdings_value": round(total_value, 2),
        "total_cost_basis": round(total_cost, 2),
        "unrealized_gain": round(total_value - total_cost, 2),
        "total_account_value": round(total_value + 8500.00, 2),
        "retirement_accounts": {
            "401k": {"balance": 42000.00, "ytd_contribution": 12000.00, "employer_match_pct": 4.0},
            "roth_ira": {"balance": 18500.00, "ytd_contribution": 4500.00},
        },
    }


def generate_income_records() -> dict:
    """Annual income summary."""
    return {
        "tax_year": datetime.now().year,
        "primary_employer": "Employer Inc.",
        "ytd_gross_income": 84000.00,
        "ytd_federal_withholding": 11200.00,
        "ytd_fica_withholding": 0.00,
        "ytd_state_withholding": 0.00,
        "filing_status": "Single",
        "notes": "FICA withholding is zero because employee is on F-1 OPT and qualifies as a nonresident alien for tax purposes.",
    }


def generate_event_timeline() -> list[dict]:
    """Major financial events in the user's history."""
    return [
        {"date": "2024-08-15", "event": "Started graduate school", "category": "Life Event"},
        {"date": "2025-01-10", "event": "Took out $45,000 federal student loan", "category": "Debt"},
        {"date": "2025-06-01", "event": "Began part-time research assistantship", "category": "Income"},
        {"date": "2026-01-15", "event": "Started Data Product internship at CHG Healthcare", "category": "Income"},
        {"date": "2026-05-15", "event": "Completed M.S. Data Science", "category": "Life Event"},
        {"date": "2026-05-20", "event": "Started OPT employment authorization period", "category": "Tax Status"},
    ]


def save_all(output_dir: str = "./sample_data") -> dict:
    """Generate and save all sample data files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    bank = generate_bank_transactions()
    bank.to_csv(output_path / "bank_transactions.csv", index=False)

    cc = generate_credit_card_transactions()
    cc.to_csv(output_path / "credit_card_transactions.csv", index=False)

    bills = generate_bills_and_utilities()
    with open(output_path / "bills.json", "w") as f:
        json.dump(bills, f, indent=2)

    loans = generate_loans_and_emis()
    with open(output_path / "loans.json", "w") as f:
        json.dump(loans, f, indent=2)

    portfolio = generate_portfolio()
    with open(output_path / "portfolio.json", "w") as f:
        json.dump(portfolio, f, indent=2, default=str)

    income = generate_income_records()
    with open(output_path / "income.json", "w") as f:
        json.dump(income, f, indent=2)

    timeline = generate_event_timeline()
    with open(output_path / "timeline.json", "w") as f:
        json.dump(timeline, f, indent=2)

    return {
        "bank": bank,
        "credit_card": cc,
        "bills": bills,
        "loans": loans,
        "portfolio": portfolio,
        "income": income,
        "timeline": timeline,
    }


if __name__ == "__main__":
    data = save_all()
    print(f"Bank transactions: {len(data['bank'])}")
    print(f"Credit card transactions: {len(data['credit_card'])}")
    print(f"Portfolio value: ${data['portfolio']['total_account_value']:,.2f}")
    print("All sample data saved to ./sample_data/")
