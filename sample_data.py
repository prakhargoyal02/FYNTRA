"""Fictional portfolio demo data for FYNTRA."""

from datetime import date, timedelta

import database as db


def load_sample_data():
    """Fill an empty FYNTRA database with deterministic fictional records."""
    if db.get_accounts():
        raise ValueError(
            "Your database already has accounts. Clear all data first to load the demo."
        )

    today = date.today()
    month_start = today.replace(day=1)

    bank = db.add_account("Main Bank", "Bank", 28000, str(month_start))
    savings = db.add_account("Savings", "Savings", 45000, str(month_start))
    cash = db.add_account("Cash", "Cash", 3000, str(month_start))
    card = db.add_account("Credit Card", "Credit Card", -7500, str(month_start))

    # Current-month ledger.
    db.add_transaction(
        month_start.isoformat(), "income", 65000, bank, "Salary",
        merchant="Employer", payment_method="Bank transfer", tags="income"
    )
    db.add_transaction(
        (month_start + timedelta(days=1)).isoformat(),
        "expense", 15000, bank, "Rent",
        merchant="Landlord", payment_method="Bank transfer", tags="fixed"
    )
    db.add_transaction(
        (month_start + timedelta(days=3)).isoformat(),
        "expense", 3200, bank, "Food",
        subcategory="Groceries", merchant="Fresh Market",
        payment_method="UPI"
    )
    db.add_transaction(
        (month_start + timedelta(days=5)).isoformat(),
        "expense", 1250, cash, "Transport",
        merchant="Metro & Auto", payment_method="Cash"
    )
    db.add_transaction(
        (month_start + timedelta(days=7)).isoformat(),
        "expense", 2499, card, "Shopping",
        merchant="Online Store", payment_method="Card", tags="personal"
    )
    db.add_transaction(
        (month_start + timedelta(days=9)).isoformat(),
        "transfer", 10000, bank, "Transfer",
        to_account_id=savings, merchant="Monthly saving",
        payment_method="Bank transfer"
    )

    # Previous months make the trend charts useful.
    for months_back, income, expenses in [
        (1, 62000, [14500, 4100, 2300, 1700]),
        (2, 60000, [14500, 3800, 1800, 2200]),
        (3, 58000, [14000, 4200, 1900, 1600]),
    ]:
        year = month_start.year
        month = month_start.month - months_back
        while month <= 0:
            month += 12
            year -= 1

        previous = date(year, month, 1)
        db.add_transaction(
            previous.isoformat(), "income", income, bank, "Salary",
            merchant="Employer", payment_method="Bank transfer"
        )

        categories = ["Rent", "Food", "Transport", "Entertainment"]
        for index, amount in enumerate(expenses):
            db.add_transaction(
                (previous + timedelta(days=index + 2)).isoformat(),
                "expense", amount, bank,
                categories[index],
                merchant=categories[index],
                payment_method="UPI",
            )

    for category, limit in [
        ("Food", 7000),
        ("Transport", 4000),
        ("Shopping", 6000),
        ("Entertainment", 3500),
    ]:
        db.save_budget(category, limit)

    db.add_goal(
        "Emergency Fund",
        150000,
        65000,
        str(today + timedelta(days=240)),
    )
    db.add_goal(
        "New Laptop",
        90000,
        24000,
        str(today + timedelta(days=150)),
    )

    db.add_debt("Education Loan", 220000, 145000, 9.5)

    db.add_bill(
        "Electricity",
        2400,
        str(today + timedelta(days=5)),
        "Utilities",
        "Monthly",
        bank,
    )
    db.add_bill(
        "Internet",
        999,
        str(today + timedelta(days=8)),
        "Utilities",
        "Monthly",
        bank,
    )

    db.add_subscription(
        "Music",
        119,
        "Monthly",
        str(today + timedelta(days=10)),
        bank,
        "Entertainment",
        "UPI",
    )
    db.add_subscription(
        "Cloud Storage",
        1300,
        "Yearly",
        str(today + timedelta(days=30)),
        card,
        "Subscriptions",
        "Card",
    )

    db.add_recurring_entry(
        "Monthly salary",
        "income",
        65000,
        bank,
        "Salary",
        "Monthly",
        str(today + timedelta(days=25)),
        merchant="Employer",
        payment_method="Bank transfer",
        tags="income",
    )
    db.add_recurring_entry(
        "Savings transfer",
        "transfer",
        10000,
        bank,
        "Transfer",
        "Monthly",
        str(today + timedelta(days=20)),
        to_account_id=savings,
        merchant="Monthly saving",
        payment_method="Bank transfer",
    )
