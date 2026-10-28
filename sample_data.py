"""Small fictional demo dataset for learning and screenshots."""

from datetime import date, timedelta
import database as db


def load_sample_data():
    """Add demo records only when no accounts exist."""
    if db.get_accounts():
        raise ValueError("Your database already has data. Clear it first if you want demo data.")

    cash = db.add_account("Cash", "Cash", 2500)
    bank = db.add_account("Main Bank", "Bank", 25000)

    today = date.today()
    month_start = today.replace(day=1)

    db.add_transaction(month_start.isoformat(), "income", 55000, bank, "Salary", "Employer")
    db.add_transaction((month_start + timedelta(days=2)).isoformat(), "expense", 12000, bank, "Rent", "Landlord")
    db.add_transaction((month_start + timedelta(days=4)).isoformat(), "expense", 2600, bank, "Food", "Groceries")
    db.add_transaction((month_start + timedelta(days=6)).isoformat(), "expense", 900, cash, "Transport", "Metro")
    db.add_transaction((month_start + timedelta(days=8)).isoformat(), "expense", 1499, bank, "Shopping", "Online Store")
    db.add_transaction((month_start + timedelta(days=10)).isoformat(), "expense", 699, bank, "Entertainment", "Movies")

    db.save_budget("Food", 6000)
    db.save_budget("Transport", 3000)
    db.save_budget("Shopping", 5000)
    db.save_budget("Entertainment", 2500)

    db.add_goal("Emergency Fund", 100000, 28000, str(today + timedelta(days=240)))
    db.add_goal("New Laptop", 80000, 12000, str(today + timedelta(days=180)))

    db.add_debt("Education Loan", 180000, 125000, 9.5)

    db.add_bill("Electricity", 2200, str(today + timedelta(days=5)), "Utilities")
    db.add_bill("Internet", 999, str(today + timedelta(days=8)), "Utilities")

    db.add_subscription("Music", 119, "Monthly", str(today + timedelta(days=12)))
    db.add_subscription("Cloud Storage", 1300, "Yearly", str(today + timedelta(days=30)))
