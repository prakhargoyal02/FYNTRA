"""
FYNTRA
======

A beginner-readable personal finance workspace built with:
Python + NumPy + Pandas + SQLite + Streamlit.

Run:
    py -m streamlit run app.py
"""

from datetime import date, timedelta

import altair as alt
import pandas as pd
import streamlit as st

import analytics as an
import csv_tools
import database as db
from sample_data import load_sample_data


st.set_page_config(
    page_title="FYNTRA",
    page_icon="💸",
    layout="wide",
)

db.setup_database()


# ------------------------------------------------------------------
# Small helpers
# ------------------------------------------------------------------

PAYMENT_METHODS = ["UPI", "Card", "Cash", "Bank transfer", "Other"]
ACCOUNT_TYPES = [
    "Bank",
    "Savings",
    "Cash",
    "Wallet",
    "Credit Card",
    "Investment",
    "Other",
]
FREQUENCIES = ["Weekly", "Monthly", "Yearly"]


def money(value):
    """Format money for display."""
    return f"₹{float(value):,.2f}"


def heading(title, text):
    st.title(title)
    st.caption(text)


def tx_frame():
    return an.transactions_frame(db.get_transactions())


def account_map():
    return {row["id"]: row["name"] for row in db.get_accounts()}


def account_select(label, accounts, key=None, default=None):
    if not accounts:
        st.warning("Create an account first.")
        st.stop()

    ids = list(accounts)
    index = ids.index(default) if default in ids else 0

    return st.selectbox(
        label,
        ids,
        index=index,
        format_func=lambda item: accounts[item],
        key=key,
    )


def refresh(message):
    st.session_state["notice"] = message
    st.rerun()


def safe_month(value):
    try:
        return pd.Period(value, freq="M").strftime("%Y-%m")
    except Exception:
        st.sidebar.error("Report month must look like YYYY-MM.")
        return date.today().strftime("%Y-%m")


if "notice" in st.session_state:
    st.success(st.session_state.pop("notice"))


# ------------------------------------------------------------------
# Navigation
# ------------------------------------------------------------------

st.sidebar.title("FYNTRA")
st.sidebar.caption("Know where your money goes. Decide where it goes next.")

page = st.sidebar.radio(
    "Navigation",
    [
        "Overview",
        "Transactions",
        "Accounts",
        "Budgets",
        "Commitments",
        "Goals & Debt",
        "Insights",
        "Planning",
        "Data & Settings",
    ],
)

report_month = safe_month(
    st.sidebar.text_input(
        "Report month",
        value=date.today().strftime("%Y-%m"),
        help="Use YYYY-MM, for example 2026-10.",
    )
)


# ------------------------------------------------------------------
# Overview
# ------------------------------------------------------------------

def overview_page():
    heading(
        "Overview",
        "Available cash, monthly flow, commitments and progress in one place.",
    )

    tx = tx_frame()
    numbers = an.overview(tx, report_month)
    balances = an.account_balances(db.get_accounts(), tx)
    available_cash = (
        float(
            balances.loc[
                ~balances["account_type"].isin(["Credit Card", "Investment"]),
                "balance",
            ].sum()
        )
        if not balances.empty
        else 0.0
    )
    net_worth = an.total_net_worth(db.get_accounts(), tx, db.get_debts())
    subscription_cost = an.monthly_subscription_cost(db.get_subscriptions())
    budget = an.budget_status(db.get_budgets(), tx, report_month)
    budget_remaining = float(budget["remaining"].sum()) if not budget.empty else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Available cash", money(available_cash))
    c2.metric("Money in", money(numbers["income"]))
    c3.metric("Money out", money(numbers["expenses"]))
    c4.metric("Budget left", money(budget_remaining))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Net cash flow", money(numbers["net"]))
    c2.metric(
        "Savings rate",
        "—" if numbers["savings_rate"] is None else f'{numbers["savings_rate"]:.1f}%',
    )
    c3.metric("Net worth", money(net_worth))
    c4.metric("Subscriptions / month", money(subscription_cost))

    left, right = st.columns([1.65, 1])

    with left:
        st.subheader("Money in motion")
        monthly = an.monthly_cash_flow(tx)

        if monthly.empty:
            st.info("Add transactions to see monthly cash flow.")
        else:
            plot = monthly.melt(
                "month",
                ["income", "expenses"],
                var_name="flow",
                value_name="amount",
            )

            chart = (
                alt.Chart(plot)
                .mark_bar()
                .encode(
                    x=alt.X("month:N", title="Month"),
                    xOffset="flow:N",
                    y=alt.Y("amount:Q", title="Amount"),
                    color="flow:N",
                    tooltip=["month", "flow", "amount"],
                )
                .properties(height=280)
            )
            st.altair_chart(chart, use_container_width=True)

        st.subheader("Recent activity")
        if tx.empty:
            st.info("No transactions yet.")
        else:
            recent = tx.head(8)[
                [
                    "transaction_date",
                    "merchant",
                    "category",
                    "kind",
                    "account_name",
                    "amount",
                ]
            ].copy()
            recent["transaction_date"] = recent["transaction_date"].dt.date
            recent["amount"] = recent["amount"].map(money)
            st.dataframe(recent, hide_index=True, use_container_width=True)

    with right:
        st.subheader("Financial pulse")

        if numbers["income"] == 0 and numbers["expenses"] == 0:
            st.info("Add this month's transactions to build your financial pulse.")
        elif numbers["net"] >= 0:
            st.success(
                f"You are positive by {money(numbers['net'])} this month."
            )
        else:
            st.warning(
                f"You are negative by {money(abs(numbers['net']))} this month."
            )

        if numbers["largest_expense"]:
            st.metric(
                "Largest expense",
                money(numbers["largest_amount"]),
                help=numbers["largest_expense"],
            )

        st.metric(
            "Average expense",
            money(numbers["average_expense"]),
        )

        st.subheader("On the horizon")
        timeline = an.timeline(
            db.get_bills(),
            db.get_subscriptions(),
            db.get_goals(),
            db.get_recurring_entries(),
        )

        today = pd.Timestamp(date.today())
        horizon = today + pd.Timedelta(days=14)
        upcoming = timeline[
            (timeline["date"] >= today) & (timeline["date"] <= horizon)
        ].head(5)

        if upcoming.empty:
            st.caption("No commitments due in the next 14 days.")
        else:
            shown = upcoming.copy()
            shown["date"] = shown["date"].dt.date
            shown["amount"] = shown["amount"].map(money)
            st.dataframe(
                shown[["date", "type", "name", "amount"]],
                hide_index=True,
                use_container_width=True,
            )


# ------------------------------------------------------------------
# Transactions
# ------------------------------------------------------------------

def transaction_form(accounts, row=None, form_key="transaction"):
    row = row or {}
    transaction_id = row.get("id")

    kind_options = ["expense", "income", "transfer"]
    current_kind = row.get("kind", "expense")
    kind_index = kind_options.index(current_kind) if current_kind in kind_options else 0

    with st.form(form_key):
        kind = st.selectbox("Type", kind_options, index=kind_index)
        on = st.date_input(
            "Date",
            value=pd.to_datetime(
                row.get("transaction_date", date.today())
            ).date(),
        )
        amount = st.number_input(
            "Amount",
            min_value=0.01,
            value=float(row.get("amount", row.get("amount_value", 100.0))),
            step=100.0,
        )

        account_id = account_select(
            "From / account",
            accounts,
            key=f"{form_key}_account",
            default=row.get("account_id"),
        )

        to_account_id = None
        if kind == "transfer":
            to_account_id = account_select(
                "To account",
                accounts,
                key=f"{form_key}_to",
                default=row.get("to_account_id"),
            )

        category = st.text_input(
            "Category",
            value=row.get("category", "Transfer" if kind == "transfer" else "Food"),
        )
        subcategory = st.text_input(
            "Subcategory",
            value=row.get("subcategory", "") or "",
        )
        merchant = st.text_input(
            "Merchant / source",
            value=row.get("merchant", "") or "",
        )

        method = row.get("payment_method", "Other") or "Other"
        method_index = PAYMENT_METHODS.index(method) if method in PAYMENT_METHODS else 4

        payment_method = st.selectbox(
            "Payment method",
            PAYMENT_METHODS,
            index=method_index,
        )
        tags = st.text_input(
            "Tags",
            value=row.get("tags", "") or "",
            help="Comma-separated labels such as work, travel, fixed.",
        )
        notes = st.text_area(
            "Notes",
            value=row.get("notes", "") or "",
        )

        submitted = st.form_submit_button(
            "Update transaction" if transaction_id else "Save transaction",
            type="primary",
        )

    if submitted:
        values = dict(
            transaction_date=on.isoformat(),
            kind=kind,
            amount=amount,
            account_id=account_id,
            category=category.strip() or "Other",
            merchant=merchant.strip(),
            notes=notes.strip(),
            to_account_id=to_account_id,
            subcategory=subcategory.strip(),
            payment_method=payment_method,
            tags=tags.strip(),
        )

        try:
            if transaction_id:
                db.update_transaction(transaction_id, **values)
                refresh("Transaction updated.")
            else:
                db.add_transaction(**values)
                refresh("Transaction saved.")
        except ValueError as error:
            st.error(str(error))


def transactions_page():
    heading(
        "Transactions",
        "Create, search, filter, edit, duplicate and schedule your ledger entries.",
    )

    accounts = account_map()

    if not accounts:
        st.warning("Create an account first in Accounts.")
        return

    history_tab, add_tab, recurring_tab = st.tabs(
        ["History", "Add transaction", "Recurring"]
    )

    with add_tab:
        transaction_form(accounts, form_key="new_transaction")

    with history_tab:
        tx = tx_frame()

        if tx.empty:
            st.info("No transactions yet.")
        else:
            search = st.text_input(
                "Search",
                placeholder="Merchant, category, tags, notes or amount...",
            )

            with st.expander("Filters"):
                c1, c2 = st.columns(2)
                start = c1.date_input(
                    "From",
                    value=pd.Period(report_month).start_time.date(),
                    key="tx_from",
                )
                end = c2.date_input(
                    "To",
                    value=pd.Period(report_month).end_time.date(),
                    key="tx_to",
                )

                categories = st.multiselect(
                    "Categories",
                    sorted(tx["category"].dropna().astype(str).unique()),
                )
                selected_accounts = st.multiselect(
                    "Accounts",
                    sorted(tx["account_name"].dropna().astype(str).unique()),
                )
                selected_kinds = st.multiselect(
                    "Types",
                    ["income", "expense", "transfer"],
                    default=["income", "expense", "transfer"],
                )
                selected_methods = st.multiselect(
                    "Payment methods",
                    sorted(
                        tx["payment_method"]
                        .fillna("Other")
                        .astype(str)
                        .unique()
                    ),
                )
                c1, c2 = st.columns(2)
                minimum = c1.number_input(
                    "Minimum amount",
                    min_value=0.0,
                    value=0.0,
                )
                maximum = c2.number_input(
                    "Maximum amount",
                    min_value=0.0,
                    value=max(float(tx["amount"].max()), 1000.0),
                )

            filtered = tx[
                tx["transaction_date"].between(
                    pd.Timestamp(start),
                    pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1),
                )
                & tx["kind"].isin(selected_kinds)
                & tx["amount"].between(minimum, maximum)
            ].copy()

            if search:
                text = (
                    filtered[
                        ["merchant", "category", "subcategory", "tags", "notes", "amount"]
                    ]
                    .fillna("")
                    .astype(str)
                    .agg(" ".join, axis=1)
                )
                filtered = filtered[
                    text.str.contains(search, case=False, regex=False)
                ]

            if categories:
                filtered = filtered[filtered["category"].isin(categories)]
            if selected_accounts:
                filtered = filtered[
                    filtered["account_name"].isin(selected_accounts)
                ]
            if selected_methods:
                filtered = filtered[
                    filtered["payment_method"].isin(selected_methods)
                ]

            order = st.selectbox(
                "Sort",
                ["Newest", "Oldest", "Largest", "Smallest"],
            )

            if order == "Newest":
                filtered = filtered.sort_values(
                    ["transaction_date", "id"],
                    ascending=[False, False],
                )
            elif order == "Oldest":
                filtered = filtered.sort_values(
                    ["transaction_date", "id"],
                    ascending=[True, True],
                )
            elif order == "Largest":
                filtered = filtered.sort_values("amount", ascending=False)
            else:
                filtered = filtered.sort_values("amount", ascending=True)

            st.caption(f"{len(filtered)} matching transactions")

            shown = filtered[
                [
                    "transaction_date",
                    "merchant",
                    "kind",
                    "category",
                    "account_name",
                    "to_account_name",
                    "payment_method",
                    "amount",
                    "tags",
                ]
            ].copy()
            shown["transaction_date"] = shown["transaction_date"].dt.date
            shown["amount"] = shown["amount"].map(money)

            st.dataframe(
                shown,
                hide_index=True,
                use_container_width=True,
            )

            if not filtered.empty:
                labels = {
                    int(row["id"]): (
                        f'#{int(row["id"])} | '
                        f'{row["transaction_date"].date()} | '
                        f'{row["merchant"] or row["category"]} | '
                        f'{money(row["amount"])}'
                    )
                    for _, row in filtered.iterrows()
                }

                selected_id = st.selectbox(
                    "Select a transaction",
                    list(labels),
                    format_func=lambda item: labels[item],
                )

                selected_row = filtered[
                    filtered["id"] == selected_id
                ].iloc[0].to_dict()

                with st.expander("Edit selected transaction"):
                    transaction_form(
                        accounts,
                        selected_row,
                        form_key=f"edit_transaction_{selected_id}",
                    )

                c1, c2 = st.columns(2)

                if c1.button("Duplicate selected transaction"):
                    db.duplicate_transaction(selected_id)
                    refresh("Transaction duplicated.")

                if c2.button("Delete selected transaction"):
                    db.delete_transaction(selected_id)
                    refresh("Transaction deleted.")

    with recurring_tab:
        st.subheader("Recurring schedules")

        with st.form("recurring_form", clear_on_submit=True):
            name = st.text_input("Schedule name", placeholder="Monthly salary")
            kind = st.selectbox(
                "Recurring type",
                ["expense", "income", "transfer"],
            )
            amount = st.number_input(
                "Recurring amount",
                min_value=0.01,
                step=100.0,
            )
            account_id = account_select(
                "From / account",
                accounts,
                key="recurring_account",
            )

            to_account_id = None
            if kind == "transfer":
                to_account_id = account_select(
                    "To account",
                    accounts,
                    key="recurring_to",
                )

            category = st.text_input(
                "Recurring category",
                value="Transfer" if kind == "transfer" else "Other",
            )
            merchant = st.text_input("Merchant / source", key="recurring_merchant")
            payment_method = st.selectbox(
                "Payment method",
                PAYMENT_METHODS,
                key="recurring_method",
            )
            tags = st.text_input("Tags", key="recurring_tags")
            notes = st.text_area("Notes", key="recurring_notes")
            frequency = st.selectbox("Frequency", FREQUENCIES)
            next_date = st.date_input(
                "Next occurrence",
                value=date.today(),
            )
            saved = st.form_submit_button(
                "Create recurring schedule",
                type="primary",
            )

        if saved:
            if not name.strip():
                st.error("Schedule name is required.")
            else:
                try:
                    db.add_recurring_entry(
                        name.strip(),
                        kind,
                        amount,
                        account_id,
                        category.strip() or "Other",
                        frequency,
                        next_date.isoformat(),
                        to_account_id,
                        merchant.strip(),
                        payment_method,
                        tags.strip(),
                        notes.strip(),
                    )
                    refresh("Recurring schedule created.")
                except ValueError as error:
                    st.error(str(error))

        if st.button("Generate all entries due today"):
            created = db.generate_due_recurring(date.today().isoformat())
            refresh(f"Generated {created} due recurring transaction(s).")

        recurring = db.get_recurring_entries()

        if not recurring:
            st.info("No recurring schedules yet.")
        else:
            table = pd.DataFrame(recurring)
            st.dataframe(
                table[
                    [
                        "name",
                        "kind",
                        "amount",
                        "account_name",
                        "to_account_name",
                        "frequency",
                        "next_date",
                        "active",
                    ]
                ],
                hide_index=True,
                use_container_width=True,
            )

            labels = {
                row["id"]: f'{row["name"]} · {row["frequency"]} · {row["next_date"]}'
                for row in recurring
            }
            recurring_id = st.selectbox(
                "Manage recurring schedule",
                list(labels),
                format_func=lambda item: labels[item],
            )
            selected = next(
                row for row in recurring if row["id"] == recurring_id
            )

            c1, c2 = st.columns(2)
            if c1.button("Pause" if selected["active"] else "Resume"):
                db.set_recurring_active(
                    recurring_id,
                    not bool(selected["active"]),
                )
                refresh("Recurring schedule updated.")

            if c2.button("Delete recurring schedule"):
                db.delete_recurring_entry(recurring_id)
                refresh("Recurring schedule deleted.")


# ------------------------------------------------------------------
# Accounts
# ------------------------------------------------------------------

def accounts_page():
    heading(
        "Accounts",
        "Bank, cash, cards, wallets, savings and investments.",
    )

    with st.form("account_form", clear_on_submit=True):
        name = st.text_input("Account name", placeholder="Main Bank")
        account_type = st.selectbox("Account type", ACCOUNT_TYPES)
        opening_balance = st.number_input(
            "Opening balance",
            value=0.0,
            step=500.0,
            help="Use a negative opening balance for money owed on a credit card.",
        )
        opening_date = st.date_input(
            "Opening date",
            value=date.today(),
        )
        saved = st.form_submit_button("Add account", type="primary")

    if saved:
        if not name.strip():
            st.error("Account name is required.")
        else:
            db.add_account(
                name.strip(),
                account_type,
                opening_balance,
                opening_date.isoformat(),
            )
            refresh("Account created.")

    accounts = db.get_accounts()
    balances = an.account_balances(accounts, tx_frame())

    if balances.empty:
        st.info("No accounts yet.")
        return

    c1, c2 = st.columns(2)
    c1.metric("Total account balance", money(balances["balance"].sum()))
    c2.metric("Number of accounts", len(balances))

    shown = balances.copy()
    shown["opening_balance"] = shown["opening_balance"].map(money)
    shown["balance"] = shown["balance"].map(money)

    st.dataframe(
        shown,
        hide_index=True,
        use_container_width=True,
    )

    names = {row["id"]: row["name"] for row in accounts}
    account_id = st.selectbox(
        "Delete account",
        list(names),
        format_func=lambda item: names[item],
    )

    if st.button("Delete selected account"):
        try:
            db.delete_account(account_id)
            refresh("Account deleted.")
        except ValueError as error:
            st.error(str(error))


# ------------------------------------------------------------------
# Budgets
# ------------------------------------------------------------------

def budgets_page():
    heading(
        "Budgets",
        "Monthly category limits, status bands and a simple affordability check.",
    )

    with st.form("budget_form", clear_on_submit=True):
        category = st.text_input("Category", placeholder="Food")
        limit = st.number_input(
            "Monthly limit",
            min_value=0.0,
            step=500.0,
        )
        saved = st.form_submit_button("Save budget", type="primary")

    if saved:
        if not category.strip() or limit <= 0:
            st.error("Enter a category and a monthly limit greater than zero.")
        else:
            db.save_budget(category.strip(), limit)
            refresh("Budget saved.")

    status = an.budget_status(
        db.get_budgets(),
        tx_frame(),
        report_month,
    )

    if status.empty:
        st.info("No budgets yet.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total limit", money(status["monthly_limit"].sum()))
        c2.metric("Total spent", money(status["spent"].sum()))
        c3.metric("Total remaining", money(status["remaining"].sum()))

        for _, item in status.iterrows():
            with st.container(border=True):
                st.subheader(item["category"])
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Limit", money(item["monthly_limit"]))
                c2.metric("Spent", money(item["spent"]))
                c3.metric("Remaining", money(item["remaining"]))
                c4.metric("Status", item["status"])

                st.progress(
                    min(max(float(item["used_percent"]) / 100, 0), 1)
                )
                st.caption(f'{item["used_percent"]:.1f}% used')

        budget_map = {
            row["id"]: row["category"] for row in db.get_budgets()
        }
        budget_id = st.selectbox(
            "Delete budget",
            list(budget_map),
            format_func=lambda item: budget_map[item],
        )
        if st.button("Delete selected budget"):
            db.delete_budget(budget_id)
            refresh("Budget deleted.")

    st.divider()
    st.subheader("Can I afford this?")

    purchase = st.number_input(
        "Purchase amount",
        min_value=0.0,
        step=500.0,
    )

    result = an.affordability(
        tx_frame(),
        report_month,
        purchase,
        db.get_budgets(),
    )

    st.write(result["message"])
    st.metric(
        "Recorded cash flow after purchase",
        money(result["cash_after_purchase"]),
    )

    if result["budget_remaining"] is not None:
        st.caption(
            "Remaining across category budgets: "
            + money(result["budget_remaining"])
        )


# ------------------------------------------------------------------
# Commitments
# ------------------------------------------------------------------

def commitments_page():
    heading(
        "Commitments",
        "Bills and subscriptions that can record real ledger payments.",
    )

    accounts = account_map()

    if not accounts:
        st.warning("Create an account before adding commitments.")
        return

    bill_tab, subscription_tab = st.tabs(["Bills", "Subscriptions"])

    with bill_tab:
        with st.form("bill_form", clear_on_submit=True):
            name = st.text_input("Bill name")
            amount = st.number_input(
                "Bill amount",
                min_value=0.0,
                step=100.0,
            )
            due_date = st.date_input("Due date")
            frequency = st.selectbox(
                "Frequency",
                ["One-time", "Weekly", "Monthly", "Yearly"],
            )
            account_id = account_select(
                "Payment account",
                accounts,
                key="bill_account",
            )
            category = st.text_input(
                "Bill category",
                value="Bills",
            )
            saved = st.form_submit_button(
                "Add bill",
                type="primary",
            )

        if saved:
            if not name.strip() or amount <= 0:
                st.error("Enter a bill name and amount.")
            else:
                db.add_bill(
                    name.strip(),
                    amount,
                    due_date.isoformat(),
                    category.strip() or "Bills",
                    frequency,
                    account_id,
                )
                refresh("Bill created.")

        bills = db.get_bills()

        if not bills:
            st.info("No bills yet.")

        for bill in bills:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.write(f'**{bill["name"]}**')
                c1.caption(
                    f'{bill["due_date"]} · {bill["frequency"]} · '
                    f'{bill["account_name"] or "No account"}'
                )
                c2.metric("Amount", money(bill["amount"]))
                c3.write("Paid ✅" if bill["paid"] else "Pending")

                if c4.button(
                    "Record payment",
                    key=f'bill_pay_{bill["id"]}',
                    disabled=bool(bill["paid"]),
                ):
                    try:
                        db.pay_bill(
                            bill["id"],
                            date.today().isoformat(),
                        )
                        refresh("Bill payment recorded.")
                    except ValueError as error:
                        st.error(str(error))

                if st.button(
                    "Delete bill",
                    key=f'bill_delete_{bill["id"]}',
                ):
                    db.delete_bill(bill["id"])
                    refresh("Bill deleted.")

    with subscription_tab:
        with st.form("subscription_form", clear_on_submit=True):
            name = st.text_input("Subscription name")
            amount = st.number_input(
                "Subscription amount",
                min_value=0.0,
                step=50.0,
            )
            cycle = st.selectbox(
                "Billing cycle",
                FREQUENCIES,
            )
            next_payment = st.date_input(
                "Next payment",
                key="subscription_next",
            )
            account_id = account_select(
                "Payment account",
                accounts,
                key="subscription_account",
            )
            category = st.text_input(
                "Subscription category",
                value="Subscriptions",
            )
            payment_method = st.selectbox(
                "Subscription payment method",
                PAYMENT_METHODS,
            )
            saved = st.form_submit_button(
                "Add subscription",
                type="primary",
            )

        if saved:
            if not name.strip() or amount <= 0:
                st.error("Enter a subscription name and amount.")
            else:
                db.add_subscription(
                    name.strip(),
                    amount,
                    cycle,
                    next_payment.isoformat(),
                    account_id,
                    category.strip() or "Subscriptions",
                    payment_method,
                )
                refresh("Subscription created.")

        subscriptions = db.get_subscriptions()

        st.metric(
            "Monthly equivalent",
            money(an.monthly_subscription_cost(subscriptions)),
        )

        if not subscriptions:
            st.info("No subscriptions yet.")

        for item in subscriptions:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.write(f'**{item["name"]}**')
                c1.caption(
                    f'{item["billing_cycle"]} · next {item["next_payment"]} · '
                    f'{item["account_name"] or "No account"}'
                )
                c2.metric("Cost", money(item["amount"]))
                c3.write("Active" if item["active"] else "Paused")

                b1, b2, b3 = st.columns(3)

                if b1.button(
                    "Record payment",
                    key=f'sub_pay_{item["id"]}',
                    disabled=not bool(item["active"]),
                ):
                    try:
                        db.record_subscription_payment(
                            item["id"],
                            date.today().isoformat(),
                        )
                        refresh("Subscription payment recorded.")
                    except ValueError as error:
                        st.error(str(error))

                if b2.button(
                    "Pause" if item["active"] else "Resume",
                    key=f'sub_active_{item["id"]}',
                ):
                    db.set_subscription_active(
                        item["id"],
                        not bool(item["active"]),
                    )
                    refresh("Subscription updated.")

                if b3.button(
                    "Delete",
                    key=f'sub_delete_{item["id"]}',
                ):
                    db.delete_subscription(item["id"])
                    refresh("Subscription deleted.")


# ------------------------------------------------------------------
# Goals and debt
# ------------------------------------------------------------------

def goals_debt_page():
    heading(
        "Goals & Debt",
        "Track savings targets and standalone debt in one planning workspace.",
    )

    goal_tab, debt_tab = st.tabs(["Savings goals", "Debt"])

    with goal_tab:
        with st.form("goal_form", clear_on_submit=True):
            name = st.text_input("Goal name", placeholder="Emergency Fund")
            target = st.number_input(
                "Target amount",
                min_value=0.0,
                step=1000.0,
            )
            saved_amount = st.number_input(
                "Already saved",
                min_value=0.0,
                step=1000.0,
            )
            target_date = st.date_input(
                "Target date",
                value=date.today() + timedelta(days=180),
            )
            saved = st.form_submit_button(
                "Add goal",
                type="primary",
            )

        if saved:
            if not name.strip() or target <= 0:
                st.error("Enter a goal name and target greater than zero.")
            else:
                db.add_goal(
                    name.strip(),
                    target,
                    saved_amount,
                    target_date.isoformat(),
                )
                refresh("Goal created.")

        goals = db.get_goals()

        if not goals:
            st.info("No savings goals yet.")

        for goal in goals:
            with st.container(border=True):
                target = float(goal["target_amount"])
                saved_value = float(goal["saved_amount"])
                progress = 0 if target <= 0 else min(saved_value / target, 1)

                st.subheader(goal["name"])
                c1, c2, c3 = st.columns(3)
                c1.metric("Saved", money(saved_value))
                c2.metric("Target", money(target))
                c3.metric("Left", money(max(target - saved_value, 0)))

                st.progress(progress)
                st.caption(
                    f'{progress * 100:.1f}% · target {goal["target_date"]}'
                )

                new_saved = st.number_input(
                    "Update saved amount",
                    min_value=0.0,
                    value=saved_value,
                    step=500.0,
                    key=f'goal_saved_{goal["id"]}',
                )

                c1, c2 = st.columns(2)

                if c1.button(
                    "Update goal",
                    key=f'goal_update_{goal["id"]}',
                ):
                    db.update_goal_saved(
                        goal["id"],
                        new_saved,
                    )
                    refresh("Goal updated.")

                if c2.button(
                    "Delete goal",
                    key=f'goal_delete_{goal["id"]}',
                ):
                    db.delete_goal(goal["id"])
                    refresh("Goal deleted.")

    with debt_tab:
        with st.form("debt_form", clear_on_submit=True):
            name = st.text_input("Debt name", placeholder="Education Loan")
            total = st.number_input(
                "Original amount",
                min_value=0.0,
                step=1000.0,
            )
            remaining = st.number_input(
                "Remaining amount",
                min_value=0.0,
                step=1000.0,
            )
            rate = st.number_input(
                "Interest rate %",
                min_value=0.0,
                step=0.1,
            )
            saved = st.form_submit_button(
                "Add debt",
                type="primary",
            )

        if saved:
            if not name.strip() or total <= 0:
                st.error("Enter a debt name and original amount.")
            else:
                db.add_debt(
                    name.strip(),
                    total,
                    remaining,
                    rate,
                )
                refresh("Debt added.")

        debts = db.get_debts()
        accounts = account_map()

        if not debts:
            st.info("No debt yet.")

        for debt in debts:
            with st.container(border=True):
                original = float(debt["total_amount"])
                remaining_value = float(debt["remaining_amount"])
                paid = max(original - remaining_value, 0)
                progress = 0 if original <= 0 else min(paid / original, 1)

                st.subheader(debt["name"])
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Original", money(original))
                c2.metric("Remaining", money(remaining_value))
                c3.metric("Paid", money(paid))
                c4.metric("Interest", f'{float(debt["interest_rate"]):.2f}%')
                st.progress(progress)

                if accounts and remaining_value > 0:
                    with st.expander("Record debt payment"):
                        principal = st.number_input(
                            "Principal",
                            min_value=0.0,
                            max_value=remaining_value,
                            step=500.0,
                            key=f'debt_principal_{debt["id"]}',
                        )
                        interest = st.number_input(
                            "Interest",
                            min_value=0.0,
                            step=100.0,
                            key=f'debt_interest_{debt["id"]}',
                        )
                        account_id = account_select(
                            "Payment account",
                            accounts,
                            key=f'debt_account_{debt["id"]}',
                        )
                        payment_date = st.date_input(
                            "Payment date",
                            value=date.today(),
                            key=f'debt_date_{debt["id"]}',
                        )

                        if st.button(
                            "Record debt payment",
                            key=f'debt_pay_{debt["id"]}',
                        ):
                            try:
                                db.record_debt_payment(
                                    debt["id"],
                                    principal,
                                    interest,
                                    account_id,
                                    payment_date.isoformat(),
                                )
                                refresh("Debt payment recorded.")
                            except ValueError as error:
                                st.error(str(error))

                if st.button(
                    "Delete debt",
                    key=f'debt_delete_{debt["id"]}',
                ):
                    try:
                        db.delete_debt(debt["id"])
                        refresh("Debt deleted.")
                    except ValueError as error:
                        st.error(str(error))


# ------------------------------------------------------------------
# Insights
# ------------------------------------------------------------------

def insights_page():
    heading(
        "Insights",
        "Pandas and NumPy turn your ledger into spending and cash-flow patterns.",
    )

    tx = tx_frame()

    if tx.empty:
        st.info("Add transactions first.")
        return

    numbers = an.overview(tx, report_month)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Transactions", numbers["transaction_count"])
    c2.metric("Average expense", money(numbers["average_expense"]))
    c3.metric(
        "Savings rate",
        "—" if numbers["savings_rate"] is None else f'{numbers["savings_rate"]:.1f}%',
    )
    c4.metric(
        "Largest expense",
        money(numbers["largest_amount"]),
        help=numbers["largest_expense"] or "No expenses",
    )

    left, right = st.columns(2)

    with left:
        st.subheader("Category breakdown")
        categories = an.category_spending(tx, report_month)

        if categories.empty:
            st.info("No category spending for this month.")
        else:
            chart = (
                alt.Chart(categories)
                .mark_bar()
                .encode(
                    x=alt.X("amount:Q", title="Amount"),
                    y=alt.Y("category:N", sort="-x", title="Category"),
                    tooltip=["category", "amount"],
                )
                .properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)

    with right:
        st.subheader("Daily spending")
        daily = an.daily_spending(tx, report_month)

        if daily.empty:
            st.info("No daily spending for this month.")
        else:
            chart = (
                alt.Chart(daily)
                .mark_area(opacity=0.35, line=True)
                .encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y("amount:Q", title="Amount"),
                    tooltip=["date:T", "amount"],
                )
                .properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)

    st.subheader("Monthly trend")
    monthly = an.monthly_cash_flow(tx)

    if not monthly.empty:
        line_data = monthly.melt(
            "month",
            ["net", "three_month_avg_expenses"],
            var_name="metric",
            value_name="amount",
        )
        chart = (
            alt.Chart(line_data)
            .mark_line(point=True)
            .encode(
                x=alt.X("month:N", title="Month"),
                y=alt.Y("amount:Q", title="Amount"),
                color="metric:N",
                tooltip=["month", "metric", "amount"],
            )
            .properties(height=300)
        )
        st.altair_chart(chart, use_container_width=True)

        table = monthly.copy()
        for column in [
            "income",
            "expenses",
            "net",
            "three_month_avg_expenses",
        ]:
            table[column] = table[column].map(money)

        st.dataframe(
            table,
            hide_index=True,
            use_container_width=True,
        )

    st.subheader("Account distribution")
    distribution = an.account_distribution(
        db.get_accounts(),
        tx,
    )

    if not distribution.empty:
        st.dataframe(
            distribution.assign(
                balance=distribution["balance"].map(money)
            ),
            hide_index=True,
            use_container_width=True,
        )


# ------------------------------------------------------------------
# Planning
# ------------------------------------------------------------------

def planning_page():
    heading(
        "Planning",
        "Monthly review, calendar-style timeline and explicit recurring generation.",
    )

    tx = tx_frame()
    numbers = an.overview(tx, report_month)
    budgets = an.budget_status(
        db.get_budgets(),
        tx,
        report_month,
    )

    st.subheader("Monthly review")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Income", money(numbers["income"]))
    c2.metric("Expenses", money(numbers["expenses"]))
    c3.metric("Net", money(numbers["net"]))
    c4.metric(
        "Savings rate",
        "—" if numbers["savings_rate"] is None else f'{numbers["savings_rate"]:.1f}%',
    )

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Largest expense",
        money(numbers["largest_amount"]),
        help=numbers["largest_expense"] or "No expenses",
    )
    c2.metric(
        "Top category",
        numbers["top_category"] or "—",
    )
    c3.metric(
        "Budgets exceeded",
        int((budgets["used_percent"] > 100).sum())
        if not budgets.empty
        else 0,
    )

    st.divider()
    st.subheader("Timeline")

    timeline = an.timeline(
        db.get_bills(),
        db.get_subscriptions(),
        db.get_goals(),
        db.get_recurring_entries(),
    )

    if timeline.empty:
        st.info("No scheduled items yet.")
    else:
        shown = timeline.copy()
        shown["date"] = shown["date"].dt.date
        shown["amount"] = shown["amount"].map(money)

        st.dataframe(
            shown,
            hide_index=True,
            use_container_width=True,
        )

    st.divider()
    st.subheader("Recurring generation")

    st.write(
        "Recurring schedules are generated only when you choose to generate them. "
        "That keeps the behavior visible and easy to explain."
    )

    if st.button("Generate recurring entries due today", key="planning_generate"):
        created = db.generate_due_recurring(date.today().isoformat())
        refresh(f"Generated {created} recurring transaction(s).")


# ------------------------------------------------------------------
# Data and settings
# ------------------------------------------------------------------

def settings_page():
    heading(
        "Data & Settings",
        "Demo data, CSV portability, full backups and local reset.",
    )

    st.subheader("Demo mode")
    st.write(
        "Load deterministic fictional data for screenshots, testing and interviews."
    )

    if st.button("Load fictional demo data"):
        try:
            load_sample_data()
            refresh("Demo data loaded.")
        except ValueError as error:
            st.error(str(error))

    st.divider()
    st.subheader("CSV export")

    st.download_button(
        "Download transactions.csv",
        data=csv_tools.transactions_csv(),
        file_name="fyntra_transactions.csv",
        mime="text/csv",
    )

    st.download_button(
        "Download transaction template",
        data=csv_tools.transaction_template_csv(),
        file_name="fyntra_transaction_template.csv",
        mime="text/csv",
    )

    st.divider()
    st.subheader("Import transactions")

    uploaded_csv = st.file_uploader(
        "Upload transaction CSV",
        type=["csv"],
        key="transaction_import",
    )

    if uploaded_csv and st.button("Import uploaded transactions"):
        try:
            count = csv_tools.import_transactions(uploaded_csv.getvalue())
            refresh(f"Imported {count} transaction(s).")
        except Exception as error:
            st.error(str(error))

    st.divider()
    st.subheader("Full FYNTRA backup")

    st.download_button(
        "Download full backup ZIP",
        data=csv_tools.export_bundle(),
        file_name="fyntra_backup.zip",
        mime="application/zip",
    )

    backup = st.file_uploader(
        "Restore full FYNTRA backup ZIP",
        type=["zip"],
        key="backup_restore",
    )
    confirm_restore = st.checkbox(
        "I understand restore replaces all current local FYNTRA data."
    )

    if (
        backup
        and confirm_restore
        and st.button("Restore uploaded backup")
    ):
        try:
            count = csv_tools.restore_bundle(backup.getvalue())
            refresh(f"Backup restored ({count} records).")
        except Exception as error:
            st.error(str(error))

    st.divider()
    st.subheader("Reset")

    st.warning("Reset permanently deletes all local FYNTRA data.")
    confirm_reset = st.checkbox(
        "I understand that reset deletes everything.",
        key="reset_confirm",
    )

    if st.button(
        "Delete all local data",
        disabled=not confirm_reset,
    ):
        db.clear_all_data()
        refresh("All local FYNTRA data deleted.")


# ------------------------------------------------------------------
# Open selected page
# ------------------------------------------------------------------

PAGES = {
    "Overview": overview_page,
    "Transactions": transactions_page,
    "Accounts": accounts_page,
    "Budgets": budgets_page,
    "Commitments": commitments_page,
    "Goals & Debt": goals_debt_page,
    "Insights": insights_page,
    "Planning": planning_page,
    "Data & Settings": settings_page,
}

PAGES[page]()
