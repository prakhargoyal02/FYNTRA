"""
FYNTRA analytics
================

This file contains finance calculations.

Pandas handles tables, filtering, grouping and joins.
NumPy handles averages, percentages and small numerical calculations.
"""

import numpy as np
import pandas as pd


TRANSACTION_COLUMNS = [
    "id",
    "transaction_date",
    "kind",
    "amount",
    "account_id",
    "to_account_id",
    "account_name",
    "to_account_name",
    "category",
    "subcategory",
    "merchant",
    "payment_method",
    "tags",
    "notes",
]


def transactions_frame(transaction_rows):
    """Convert database records into a predictable Pandas DataFrame."""
    if not transaction_rows:
        return pd.DataFrame(columns=TRANSACTION_COLUMNS)

    df = pd.DataFrame(transaction_rows)

    for column in TRANSACTION_COLUMNS:
        if column not in df:
            df[column] = None

    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    return df


def month_data(df, month):
    """Return transactions only from YYYY-MM."""
    if df.empty:
        return df.copy()

    month_text = pd.Period(month, freq="M").strftime("%Y-%m")
    return df[df["transaction_date"].dt.strftime("%Y-%m") == month_text].copy()


def overview(df, month):
    """Main dashboard and monthly-review numbers."""
    data = month_data(df, month)

    income = float(data.loc[data["kind"] == "income", "amount"].sum())
    expenses = float(data.loc[data["kind"] == "expense", "amount"].sum())
    net = income - expenses

    expense_rows = data[data["kind"] == "expense"]
    expense_values = expense_rows["amount"].to_numpy(dtype=float)

    savings_rate = None
    if income > 0:
        savings_rate = float(np.round((net / income) * 100, 1))

    largest_expense = None
    largest_amount = 0.0
    if not expense_rows.empty:
        largest = expense_rows.loc[expense_rows["amount"].idxmax()]
        largest_expense = largest.get("merchant") or largest.get("category")
        largest_amount = float(largest["amount"])

    categories = category_spending(df, month)
    top_category = None if categories.empty else str(categories.iloc[0]["category"])

    return {
        "income": income,
        "expenses": expenses,
        "net": net,
        "savings_rate": savings_rate,
        "average_expense": float(np.mean(expense_values)) if expense_values.size else 0.0,
        "transaction_count": int(len(data)),
        "largest_expense": largest_expense,
        "largest_amount": largest_amount,
        "top_category": top_category,
    }


def category_spending(df, month):
    """Total expense spending per category."""
    expenses = month_data(df, month)
    expenses = expenses[expenses["kind"] == "expense"]

    if expenses.empty:
        return pd.DataFrame(columns=["category", "amount"])

    return (
        expenses.groupby("category", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
    )


def daily_spending(df, month):
    """Expense total per calendar day."""
    expenses = month_data(df, month)
    expenses = expenses[expenses["kind"] == "expense"].copy()

    if expenses.empty:
        return pd.DataFrame(columns=["date", "amount"])

    expenses["date"] = expenses["transaction_date"].dt.date

    return (
        expenses.groupby("date", as_index=False)["amount"]
        .sum()
        .sort_values("date")
    )


def monthly_cash_flow(df):
    """Income, expenses and net cash flow by month."""
    if df.empty:
        return pd.DataFrame(columns=["month", "income", "expenses", "net"])

    data = df[df["kind"].isin(["income", "expense"])].copy()

    if data.empty:
        return pd.DataFrame(columns=["month", "income", "expenses", "net"])

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
    summary["three_month_avg_expenses"] = (
        summary["expenses"].rolling(3, min_periods=1).mean().round(2)
    )

    return summary[
        ["month", "income", "expenses", "net", "three_month_avg_expenses"]
    ]


def budget_status(budget_rows, df, month):
    """Compare category budgets with actual expense spending."""
    if not budget_rows:
        return pd.DataFrame(
            columns=[
                "id",
                "category",
                "monthly_limit",
                "spent",
                "remaining",
                "used_percent",
                "status",
            ]
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

    result["status"] = np.select(
        [
            result["used_percent"] > 100,
            result["used_percent"] >= 85,
            result["used_percent"] >= 60,
        ],
        ["Over budget", "Almost full", "Watch"],
        default="Healthy",
    )

    return result[
        [
            "id",
            "category",
            "monthly_limit",
            "spent",
            "remaining",
            "used_percent",
            "status",
        ]
    ]


def account_balances(account_rows, df):
    """
    Calculate live account balances.

    Income adds to the source account.
    Expense subtracts from the source account.
    Transfer subtracts from source and adds to destination.
    """
    if not account_rows:
        return pd.DataFrame(
            columns=["id", "name", "account_type", "opening_balance", "balance"]
        )

    accounts = pd.DataFrame(account_rows)
    result = []

    for account in accounts.to_dict("records"):
        balance = float(account["opening_balance"])

        if not df.empty:
            source = df[df["account_id"] == account["id"]]
            destination = df[
                (df["kind"] == "transfer")
                & (df["to_account_id"] == account["id"])
            ]

            balance += float(source.loc[source["kind"] == "income", "amount"].sum())
            balance -= float(source.loc[source["kind"] == "expense", "amount"].sum())
            balance -= float(source.loc[source["kind"] == "transfer", "amount"].sum())
            balance += float(destination["amount"].sum())

        result.append(
            {
                "id": account["id"],
                "name": account["name"],
                "account_type": account["account_type"],
                "opening_balance": float(account["opening_balance"]),
                "balance": balance,
            }
        )

    return pd.DataFrame(result)


def account_distribution(account_rows, df):
    """Account balances for a distribution chart."""
    balances = account_balances(account_rows, df)

    if balances.empty:
        return pd.DataFrame(columns=["name", "balance"])

    return balances[["name", "balance"]].sort_values("balance", ascending=False)


def total_net_worth(account_rows, df, debt_rows):
    """Net worth = account balances minus standalone debt."""
    balances = account_balances(account_rows, df)
    assets = float(balances["balance"].sum()) if not balances.empty else 0.0

    debt = 0.0
    if debt_rows:
        debt = float(
            pd.DataFrame(debt_rows)["remaining_amount"]
            .astype(float)
            .sum()
        )

    return assets - debt


def monthly_subscription_cost(subscription_rows):
    """Convert active subscriptions to a monthly equivalent."""
    if not subscription_rows:
        return 0.0

    monthly = []

    for item in subscription_rows:
        if not item["active"]:
            continue

        amount = float(item["amount"])
        cycle = item["billing_cycle"]

        if cycle == "Weekly":
            monthly.append(amount * 52 / 12)
        elif cycle == "Yearly":
            monthly.append(amount / 12)
        else:
            monthly.append(amount)

    return float(np.round(np.sum(monthly), 2)) if monthly else 0.0


def affordability(df, month, purchase_amount, budget_rows=None):
    """
    Simple arithmetic affordability check.

    This is not financial advice.
    It compares the requested purchase with this month's remaining cash flow
    and optional remaining category budgets.
    """
    numbers = overview(df, month)
    cash_after_purchase = numbers["net"] - float(purchase_amount)

    budget_remaining = None
    if budget_rows:
        status = budget_status(budget_rows, df, month)
        budget_remaining = float(status["remaining"].sum())

    if purchase_amount <= 0:
        message = "Enter a purchase amount."
    elif cash_after_purchase >= 0:
        message = "This purchase fits inside this month's recorded cash flow."
    else:
        message = "This purchase is larger than this month's recorded cash flow."

    return {
        "cash_after_purchase": cash_after_purchase,
        "budget_remaining": budget_remaining,
        "message": message,
    }


def timeline(bill_rows, subscription_rows, goal_rows, recurring_rows):
    """Combine future commitments into one chronological DataFrame."""
    items = []

    for bill in bill_rows:
        if not bill["paid"]:
            items.append(
                {
                    "date": bill["due_date"],
                    "type": "Bill",
                    "name": bill["name"],
                    "amount": float(bill["amount"]),
                    "status": "Due",
                }
            )

    for item in subscription_rows:
        if item["active"] and item["next_payment"]:
            items.append(
                {
                    "date": item["next_payment"],
                    "type": "Subscription",
                    "name": item["name"],
                    "amount": float(item["amount"]),
                    "status": "Active",
                }
            )

    for goal in goal_rows:
        if goal["target_date"]:
            items.append(
                {
                    "date": goal["target_date"],
                    "type": "Goal",
                    "name": goal["name"],
                    "amount": max(
                        float(goal["target_amount"]) - float(goal["saved_amount"]),
                        0,
                    ),
                    "status": "Target",
                }
            )

    for item in recurring_rows:
        if item["active"]:
            items.append(
                {
                    "date": item["next_date"],
                    "type": "Recurring",
                    "name": item["name"],
                    "amount": float(item["amount"]),
                    "status": item["frequency"],
                }
            )

    if not items:
        return pd.DataFrame(columns=["date", "type", "name", "amount", "status"])

    frame = pd.DataFrame(items)
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.sort_values(["date", "type", "name"]).reset_index(drop=True)
