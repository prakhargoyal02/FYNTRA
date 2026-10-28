"""
FYNTRA analytics
================

This file turns raw database records into useful finance information.

Pandas:
- filtering
- grouping
- monthly summaries
- category summaries

NumPy:
- averages
- percentages
- safe calculations
- projections
"""

import numpy as np
import pandas as pd


def transactions_frame(transaction_rows):
    """Convert transaction dictionaries into a clean Pandas DataFrame."""
    if not transaction_rows:
        return pd.DataFrame(
            columns=[
                "id",
                "transaction_date",
                "kind",
                "amount",
                "account_id",
                "account_name",
                "category",
                "merchant",
                "notes",
            ]
        )

    df = pd.DataFrame(transaction_rows)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    return df


def month_data(df, month):
    """Return transactions only for YYYY-MM."""
    if df.empty:
        return df.copy()

    month_text = pd.Period(month, freq="M").strftime("%Y-%m")
    return df[df["transaction_date"].dt.strftime("%Y-%m") == month_text].copy()


def overview(df, month):
    """Main dashboard numbers for one month."""
    data = month_data(df, month)

    if data.empty:
        return {
            "income": 0.0,
            "expenses": 0.0,
            "net": 0.0,
            "savings_rate": None,
            "average_expense": 0.0,
            "transaction_count": 0,
        }

    income = float(data.loc[data["kind"] == "income", "amount"].sum())
    expenses = float(data.loc[data["kind"] == "expense", "amount"].sum())
    net = income - expenses

    savings_rate = None
    if income > 0:
        savings_rate = float(np.round((net / income) * 100, 1))

    expense_values = data.loc[data["kind"] == "expense", "amount"].to_numpy(dtype=float)
    average_expense = float(np.mean(expense_values)) if expense_values.size else 0.0

    return {
        "income": income,
        "expenses": expenses,
        "net": net,
        "savings_rate": savings_rate,
        "average_expense": average_expense,
        "transaction_count": int(len(data)),
    }


def category_spending(df, month):
    """How much was spent in each category this month."""
    data = month_data(df, month)
    expenses = data[data["kind"] == "expense"]

    if expenses.empty:
        return pd.DataFrame(columns=["category", "amount"])

    return (
        expenses.groupby("category", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
    )


def monthly_cash_flow(df):
    """Income, expenses and net cash flow by month."""
    if df.empty:
        return pd.DataFrame(columns=["month", "income", "expenses", "net"])

    data = df.copy()
    data["month"] = data["transaction_date"].dt.to_period("M").astype(str)

    summary = (
        data.pivot_table(
            index="month",
            columns="kind",
            values="amount",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )

    if "income" not in summary:
        summary["income"] = 0.0
    if "expense" not in summary:
        summary["expense"] = 0.0

    summary["expenses"] = summary["expense"]
    summary["net"] = summary["income"] - summary["expenses"]

    return summary[["month", "income", "expenses", "net"]]


def budget_status(budget_rows, df, month):
    """Compare each budget with actual spending."""
    if not budget_rows:
        return pd.DataFrame(
            columns=["category", "monthly_limit", "spent", "remaining", "used_percent"]
        )

    budgets = pd.DataFrame(budget_rows)
    spending = category_spending(df, month)

    result = budgets.merge(spending, on="category", how="left")
    result["amount"] = result["amount"].fillna(0.0)
    result = result.rename(columns={"amount": "spent"})
    result["remaining"] = result["monthly_limit"] - result["spent"]
    result["used_percent"] = np.where(
        result["monthly_limit"] > 0,
        (result["spent"] / result["monthly_limit"]) * 100,
        0,
    )

    return result[["id", "category", "monthly_limit", "spent", "remaining", "used_percent"]]


def account_balances(account_rows, df):
    """Calculate live account balances from opening balance + transactions."""
    if not account_rows:
        return pd.DataFrame(columns=["id", "name", "account_type", "balance"])

    accounts = pd.DataFrame(account_rows)
    balances = []

    for account in accounts.to_dict("records"):
        opening = float(account["opening_balance"])

        if df.empty:
            movement = 0.0
        else:
            account_tx = df[df["account_id"] == account["id"]]
            income = account_tx.loc[account_tx["kind"] == "income", "amount"].sum()
            expenses = account_tx.loc[account_tx["kind"] == "expense", "amount"].sum()
            movement = float(income - expenses)

        balances.append(
            {
                "id": account["id"],
                "name": account["name"],
                "account_type": account["account_type"],
                "balance": opening + movement,
            }
        )

    return pd.DataFrame(balances)


def total_net_worth(account_rows, df, debt_rows):
    """Simple net worth = account balances - remaining debt."""
    balances = account_balances(account_rows, df)
    assets = float(balances["balance"].sum()) if not balances.empty else 0.0

    debt = 0.0
    if debt_rows:
        debt = float(pd.DataFrame(debt_rows)["remaining_amount"].astype(float).sum())

    return assets - debt


def monthly_subscription_cost(subscription_rows):
    """Convert subscriptions to a monthly estimate."""
    if not subscription_rows:
        return 0.0

    total = 0.0
    for item in subscription_rows:
        if not item["active"]:
            continue

        amount = float(item["amount"])
        cycle = item["billing_cycle"]

        if cycle == "Weekly":
            total += amount * 52 / 12
        elif cycle == "Yearly":
            total += amount / 12
        else:
            total += amount

    return float(np.round(total, 2))
