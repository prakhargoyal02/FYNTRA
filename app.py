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
from ui import (
    GOLD,
    MINT,
    brand,
    cash_flow_chart,
    hero,
    metrics,
    progress_card,
    rows,
    rupees,
    style,
)


# ------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------

st.set_page_config(
    page_title="FYNTRA",
    page_icon="💸",
    layout="wide",
)

style()
db.setup_database()


# ------------------------------------------------------------------
# Constants and small helpers
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
BILL_FREQUENCIES = ["One-time", "Weekly", "Monthly", "Yearly"]


def money(value):
    """Display rupees using Indian number grouping."""
    return rupees(value, decimals=True)


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


def page_heading(title, subtitle, kicker=None):
    hero(title, subtitle, kicker or title.upper())


def overview_numbers():
    tx = tx_frame()
    numbers = an.overview(tx, report_month)
    balances = an.account_balances(db.get_accounts(), tx)

    available_cash = 0.0
    if not balances.empty:
        available_cash = float(
            balances.loc[
                ~balances["account_type"].isin(["Credit Card", "Investment"]),
                "balance",
            ].sum()
        )

    net_worth = an.total_net_worth(db.get_accounts(), tx, db.get_debts())
    subscription_cost = an.monthly_subscription_cost(db.get_subscriptions())
    budget = an.budget_status(db.get_budgets(), tx, report_month)
    budget_remaining = float(budget["remaining"].sum()) if not budget.empty else 0.0

    return {
        "tx": tx,
        "numbers": numbers,
        "balances": balances,
        "available_cash": available_cash,
        "net_worth": net_worth,
        "subscription_cost": subscription_cost,
        "budget": budget,
        "budget_remaining": budget_remaining,
    }


if "notice" in st.session_state:
    st.success(st.session_state.pop("notice"))


# ------------------------------------------------------------------
# Sidebar navigation
# ------------------------------------------------------------------

with st.sidebar:
    brand()
    st.caption("Know where your money goes. Decide where it goes next.")

    page = st.radio(
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
        st.text_input(
            "Report month",
            value=date.today().strftime("%Y-%m"),
            help="Use YYYY-MM, for example 2026-10.",
        )
    )

    st.caption("Local-first workspace · SQLite")


# ------------------------------------------------------------------
# Overview
# ------------------------------------------------------------------

def overview_page():
    data = overview_numbers()
    tx = data["tx"]
    numbers = data["numbers"]

    page_heading(
        "A clearer view. A calmer month.",
        "Know where your money goes. Decide where it goes next.",
        pd.Period(report_month).strftime("%B %Y").upper() + " / OVERVIEW",
    )

    metrics(
        [
            (
                "Available cash",
                money(data["available_cash"]),
                "Current non-investment, non-card account balances.",
            ),
            (
                "Money in",
                money(numbers["income"]),
                "Recorded income in the selected month.",
            ),
            (
                "Money out",
                money(numbers["expenses"]),
                "Recorded expenses. Transfers are excluded.",
            ),
            (
                "Budget left",
                money(data["budget_remaining"]),
                "Category budget limits minus recorded spending.",
            ),
        ]
    )

    left, right = st.columns([1.8, 1], gap="large")

    with left:
        st.subheader("Your money in motion")
        monthly = an.monthly_cash_flow(tx)
        chart = cash_flow_chart(monthly.tail(6))

        if chart is None:
            st.info("Add transactions to see monthly cash flow.")
        else:
            st.altair_chart(chart, use_container_width=True)

        st.subheader("Latest activity")
        if tx.empty:
            st.info("Add your first transaction to see activity here.")
        else:
            rows(tx, limit=8)

    with right:
        with st.container(border=True):
            st.caption("FINANCIAL PULSE")

            if numbers["income"] == 0 and numbers["expenses"] == 0:
                st.subheader("Waiting for this month's data")
                st.write("Add transactions to build a useful monthly pulse.")
            elif numbers["net"] >= 0:
                st.subheader("Positive cash flow")
                st.write(
                    f"You are ahead by **{money(numbers['net'])}** "
                    "for the selected month."
                )
            else:
                st.subheader("Cash flow needs attention")
                st.write(
                    f"Spending is ahead of income by "
                    f"**{money(abs(numbers['net']))}** this month."
                )

            if not data["budget"].empty:
                total_limit = float(data["budget"]["monthly_limit"].sum())
                total_spent = float(data["budget"]["spent"].sum())
                if total_limit > 0:
                    st.progress(min(max(total_spent / total_limit, 0), 1))
                    st.caption(
                        f"{money(total_spent)} of {money(total_limit)} "
                        "category budget used"
                    )

            if numbers["largest_expense"]:
                st.caption(
                    f"Largest expense: {numbers['largest_expense']} · "
                    f"{money(numbers['largest_amount'])}"
                )

        st.subheader("On the horizon")
        timeline = an.timeline(
            db.get_bills(),
            db.get_subscriptions(),
            db.get_goals(),
            db.get_recurring_entries(),
        )

        now = pd.Timestamp(date.today())
        horizon = now + pd.Timedelta(days=14)

        if timeline.empty:
            upcoming = timeline
        else:
            upcoming = timeline[
                (timeline["date"] >= now) & (timeline["date"] <= horizon)
            ].head(5)

        if upcoming.empty:
            st.caption("No commitments due in the next 14 days.")
        else:
            for item in upcoming.to_dict("records"):
                with st.container(border=True):
                    st.write(f'**{item["name"]}** · {money(item["amount"])}')
                    st.caption(
                        f'{pd.Timestamp(item["date"]).date()} · '
                        f'{item["type"]} · {item["status"]}'
                    )

    metrics(
        [
            (
                "Cash saved",
                money(numbers["net"]),
                "Income minus expenses for the selected month.",
            ),
            (
                "Savings rate",
                "—"
                if numbers["savings_rate"] is None
                else f'{numbers["savings_rate"]:.1f}%',
                "Net cash flow divided by income.",
            ),
            (
                "Net worth",
                money(data["net_worth"]),
                "Account balances minus standalone debt.",
            ),
            (
                "Subscriptions / month",
                money(data["subscription_cost"]),
                "Monthly equivalent of active subscriptions.",
            ),
        ]
    )

    goals = db.get_goals()
    debts = db.get_debts()

    with st.expander("Savings goals & debt"):
        if not goals and not debts:
            st.caption("Add a goal or debt to see progress here.")

        for goal in goals:
            progress_card(
                goal["name"],
                goal["saved_amount"],
                goal["target_amount"],
                goal["target_date"] or "No target date",
            )

        if debts:
            st.subheader("Debt snapshot")
            for debt in debts:
                paid = max(
                    float(debt["total_amount"]) - float(debt["remaining_amount"]),
                    0,
                )
                progress_card(
                    debt["name"],
                    paid,
                    debt["total_amount"],
                    f'{money(debt["remaining_amount"])} remaining',
                )


# ------------------------------------------------------------------
# Transactions
# ------------------------------------------------------------------

def transaction_form(accounts, row=None, form_key="transaction"):
    row = row or {}
    transaction_id = row.get("id")

    kind_options = ["expense", "income", "transfer"]
    current_kind = row.get("kind", "expense")

    kind = st.segmented_control(
        "Direction",
        kind_options,
        default=current_kind,
        key=f"{form_key}_direction",
    ) or current_kind

    with st.form(form_key):
        c1, c2 = st.columns(2)
        on = c1.date_input(
            "Date",
            value=pd.to_datetime(
                row.get("transaction_date", date.today())
            ).date(),
        )
        amount = c2.number_input(
            "Amount",
            min_value=0.01,
            value=float(row.get("amount", 100.0)),
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

        c1, c2 = st.columns(2)
        category = c1.text_input(
            "Category",
            value=row.get(
                "category",
                "Transfer" if kind == "transfer" else "Food",
            ),
        )
        subcategory = c2.text_input(
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
            use_container_width=True,
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


def recurring_page(accounts):
    st.subheader("Recurring entries")
    st.caption(
        "Create schedules for salary, rent, transfers, SIP-style entries and "
        "other repeating money movements."
    )

    with st.expander("Create recurring schedule", expanded=False):
        with st.form("recurring_form", clear_on_submit=True):
            name = st.text_input("Schedule name", placeholder="Monthly salary")
            kind = st.selectbox("Type", ["income", "expense", "transfer"])
            amount = st.number_input("Amount", min_value=0.01, step=100.0)
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
                "Category",
                value="Salary" if kind == "income" else (
                    "Transfer" if kind == "transfer" else "Bills"
                ),
            )
            merchant = st.text_input("Merchant / source")
            payment_method = st.selectbox("Payment method", PAYMENT_METHODS)
            tags = st.text_input("Tags")
            notes = st.text_area("Notes")
            frequency = st.selectbox("Frequency", FREQUENCIES)
            next_date = st.date_input("Next date", value=date.today())

            submitted = st.form_submit_button(
                "Save recurring schedule",
                type="primary",
            )

        if submitted:
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
                        to_account_id=to_account_id,
                        merchant=merchant.strip(),
                        payment_method=payment_method,
                        tags=tags.strip(),
                        notes=notes.strip(),
                    )
                    refresh("Recurring schedule created.")
                except ValueError as error:
                    st.error(str(error))

    schedules = db.get_recurring_entries()

    c1, c2 = st.columns([1, 2])
    until = c1.date_input(
        "Generate due entries through",
        value=date.today(),
        key="generate_until",
    )

    if c2.button("Generate due recurring entries", type="primary"):
        created = db.generate_due_recurring(until.isoformat())
        refresh(f"Generated {created} recurring transaction(s).")

    if not schedules:
        st.info("No recurring schedules yet.")
        return

    for item in schedules:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.write(f'**{item["name"]}**')
            c1.caption(
                f'{item["frequency"]} · next {item["next_date"]} · '
                f'{item["category"]}'
            )
            c2.metric("Amount", money(item["amount"]))
            c3.write("Active" if item["active"] else "Paused")

            b1, b2 = st.columns(2)
            if b1.button(
                "Pause" if item["active"] else "Resume",
                key=f'recurring_toggle_{item["id"]}',
            ):
                db.set_recurring_active(item["id"], not bool(item["active"]))
                refresh("Recurring schedule updated.")

            if b2.button(
                "Delete",
                key=f'recurring_delete_{item["id"]}',
            ):
                db.delete_recurring_entry(item["id"])
                refresh("Recurring schedule deleted.")


def transactions_page():
    page_heading(
        "Every move, accounted for.",
        "Search your ledger, record a payment, or plan a recurring entry.",
        "TRANSACTIONS",
    )

    accounts = account_map()

    if not accounts:
        st.warning("Create an account first in Accounts.")
        return

    mode = st.segmented_control(
        "View",
        ["History", "Add transaction", "Recurring"],
        default="History",
    )

    if mode == "Add transaction":
        transaction_form(accounts, form_key="new_transaction")
        return

    if mode == "Recurring":
        recurring_page(accounts)
        return

    tx = tx_frame()

    if tx.empty:
        st.info("No transactions yet.")
        return

    search = st.text_input(
        "Search transactions",
        placeholder="Merchant, note, category, tag or amount",
    )

    with st.expander("Filters", expanded=False):
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
        tag = st.text_input("Tag filter")

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
                [
                    "merchant",
                    "category",
                    "subcategory",
                    "tags",
                    "notes",
                    "amount",
                ]
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
        filtered = filtered[filtered["account_name"].isin(selected_accounts)]
    if selected_methods:
        filtered = filtered[filtered["payment_method"].isin(selected_methods)]
    if tag:
        filtered = filtered[
            filtered["tags"].fillna("").str.contains(
                tag,
                case=False,
                regex=False,
            )
        ]

    order = st.selectbox(
        "Sort by",
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

    if filtered.empty:
        return

    labels = {
        int(record["id"]): (
            f'#{int(record["id"])} · '
            f'{record["transaction_date"].date()} · '
            f'{record["merchant"] or record["category"]} · '
            f'{money(record["amount"])}'
        )
        for _, record in filtered.iterrows()
    }

    selected = st.selectbox(
        "Select transaction",
        [None] + list(labels),
        format_func=lambda item: (
            "Choose a transaction"
            if item is None
            else labels[item]
        ),
    )

    if selected is not None:
        record = filtered.loc[filtered["id"] == selected].iloc[0].to_dict()

        with st.expander("Edit selected transaction", expanded=True):
            transaction_form(
                accounts,
                row=record,
                form_key=f"edit_transaction_{selected}",
            )

            c1, c2 = st.columns(2)
            if c1.button(
                "Duplicate transaction",
                key=f"duplicate_{selected}",
            ):
                db.duplicate_transaction(selected)
                refresh("Transaction duplicated.")

            if c2.button(
                "Delete transaction",
                key=f"delete_{selected}",
            ):
                db.delete_transaction(selected)
                refresh("Transaction deleted.")

    with st.expander("Monthly category and daily totals"):
        c1, c2 = st.columns(2)
        c1.dataframe(
            an.category_spending(tx, report_month),
            hide_index=True,
            use_container_width=True,
        )
        c2.dataframe(
            an.daily_spending(tx, report_month),
            hide_index=True,
            use_container_width=True,
        )


# ------------------------------------------------------------------
# Accounts
# ------------------------------------------------------------------

def accounts_page():
    page_heading(
        "One view of every account.",
        "Balances come from opening amounts and your recorded money movements.",
        "ACCOUNTS",
    )

    accounts = db.get_accounts()
    tx = tx_frame()
    balances = an.account_balances(accounts, tx)

    if balances.empty:
        st.info("Create your first account below.")
    else:
        for item in balances.to_dict("records"):
            account_id = item["id"]

            if tx.empty:
                inflow = 0.0
                outflow = 0.0
                latest = "No activity yet"
            else:
                source = tx[tx["account_id"] == account_id]
                destination = tx[
                    (tx["kind"] == "transfer")
                    & (tx["to_account_id"] == account_id)
                ]

                inflow = float(
                    source.loc[source["kind"] == "income", "amount"].sum()
                    + destination["amount"].sum()
                )
                outflow = float(
                    source.loc[
                        source["kind"].isin(["expense", "transfer"]),
                        "amount",
                    ].sum()
                )

                dates = pd.concat(
                    [
                        source["transaction_date"],
                        destination["transaction_date"],
                    ]
                )
                latest = (
                    dates.max().date()
                    if not dates.empty
                    else "No activity yet"
                )

            with st.container(border=True):
                st.subheader(item["name"])
                metrics(
                    [
                        ("Balance", money(item["balance"]), item["account_type"]),
                        (
                            "Inflow",
                            money(inflow),
                            "Income plus incoming transfers.",
                        ),
                        (
                            "Outflow",
                            money(outflow),
                            "Expenses plus outgoing transfers.",
                        ),
                    ]
                )
                st.caption(f"Latest activity: {latest}")

    st.caption(
        "Credit cards can use negative balances for amounts owed. "
        "A card repayment is a transfer to that account."
    )

    with st.expander(
        "Create account",
        expanded=balances.empty,
    ):
        with st.form("account_form", clear_on_submit=True):
            name = st.text_input("Account name", placeholder="Main Bank")
            account_type = st.selectbox("Account type", ACCOUNT_TYPES)
            c1, c2 = st.columns(2)
            opening = c1.number_input(
                "Opening balance",
                value=0.0,
                step=500.0,
            )
            opening_date = c2.date_input(
                "Opening date",
                value=date.today(),
            )
            submitted = st.form_submit_button(
                "Add account",
                type="primary",
            )

        if submitted:
            if not name.strip():
                st.error("Account name is required.")
            else:
                db.add_account(
                    name.strip(),
                    account_type,
                    opening,
                    opening_date.isoformat(),
                )
                refresh("Account created.")

    if accounts:
        names = {row["id"]: row["name"] for row in accounts}
        delete_id = st.selectbox(
            "Delete account",
            list(names),
            format_func=lambda item: names[item],
        )

        if st.button("Delete selected account"):
            try:
                db.delete_account(delete_id)
                refresh("Account deleted.")
            except ValueError as error:
                st.error(str(error))


# ------------------------------------------------------------------
# Budgets
# ------------------------------------------------------------------

def budgets_page():
    page_heading(
        "Give your money direction.",
        "Set category limits and see how much room remains.",
        "BUDGETS / " + report_month,
    )

    tx = tx_frame()
    status = an.budget_status(db.get_budgets(), tx, report_month)
    numbers = an.overview(tx, report_month)

    total_limit = (
        float(status["monthly_limit"].sum())
        if not status.empty
        else 0.0
    )
    total_spent = numbers["expenses"]
    remaining = total_limit - total_spent

    metrics(
        [
            (
                "Monthly limit",
                money(total_limit),
                "Sum of your category budgets.",
            ),
            (
                "Spent",
                money(total_spent),
                "All recorded expenses this month.",
            ),
            (
                "Remaining",
                money(remaining),
                "Budget limit minus monthly expenses.",
            ),
        ]
    )

    if status.empty:
        st.info("No budgets yet.")
    else:
        for item in status.to_dict("records"):
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                c1.write(f'**{item["category"]}** · {item["status"]}')
                c2.write(
                    f'{money(item["spent"])} / '
                    f'{money(item["monthly_limit"])}'
                )
                st.progress(
                    min(max(float(item["used_percent"]) / 100, 0), 1)
                )
                st.caption(
                    f'{money(item["remaining"])} remaining · '
                    f'{item["used_percent"]:.0f}% used'
                )

    st.caption(
        "Healthy <60% · Watch 60–85% · Almost full 85–100% · "
        "Over budget >100%."
    )

    with st.expander("Create or update a budget"):
        with st.form("budget_form", clear_on_submit=True):
            category = st.text_input("Category", placeholder="Food")
            limit = st.number_input(
                "Monthly category limit",
                min_value=0.0,
                step=500.0,
            )
            submitted = st.form_submit_button(
                "Save budget",
                type="primary",
            )

        if submitted:
            if not category.strip() or limit <= 0:
                st.error("Enter a category and a budget greater than zero.")
            else:
                db.save_budget(category.strip(), limit)
                refresh("Budget saved.")

    if not status.empty:
        budget_map = {
            int(row["id"]): row["category"]
            for _, row in status.iterrows()
        }
        delete_id = st.selectbox(
            "Delete budget",
            list(budget_map),
            format_func=lambda item: budget_map[item],
        )
        if st.button("Delete selected budget"):
            db.delete_budget(delete_id)
            refresh("Budget deleted.")

    st.subheader("Can it fit this month?")
    purchase = st.number_input(
        "Planned purchase",
        min_value=0.0,
        value=1000.0,
        step=100.0,
    )
    answer = an.affordability(
        tx,
        report_month,
        purchase,
        db.get_budgets(),
    )
    st.metric(
        "Cash flow after purchase",
        money(answer["cash_after_purchase"]),
    )
    st.caption(answer["message"])
    st.caption(
        "This is arithmetic based on your recorded data, not financial advice."
    )


# ------------------------------------------------------------------
# Commitments
# ------------------------------------------------------------------

def commitments_page():
    page_heading(
        "Know what is coming before it arrives.",
        "Bills and subscriptions stay visible, and payments can write directly to your ledger.",
        "COMMITMENTS",
    )

    accounts = account_map()
    bills_tab, subs_tab = st.tabs(["Bills", "Subscriptions"])

    with bills_tab:
        with st.expander("Add bill"):
            if not accounts:
                st.info("Create an account before attaching a bill payment.")
            else:
                with st.form("bill_form", clear_on_submit=True):
                    name = st.text_input("Bill name", placeholder="Electricity")
                    amount = st.number_input(
                        "Bill amount",
                        min_value=0.0,
                        step=100.0,
                    )
                    due_date = st.date_input("Due date", value=date.today())
                    frequency = st.selectbox(
                        "Frequency",
                        BILL_FREQUENCIES,
                    )
                    category = st.text_input(
                        "Category",
                        value="Bills",
                    )
                    account_id = account_select(
                        "Payment account",
                        accounts,
                        key="bill_account",
                    )
                    submitted = st.form_submit_button(
                        "Add bill",
                        type="primary",
                    )

                if submitted:
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
                        refresh("Bill added.")

        bills = db.get_bills()

        if not bills:
            st.info("No bills yet.")

        for bill in bills:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.write(f'**{bill["name"]}**')
                c1.caption(
                    f'{bill["due_date"]} · {bill["frequency"]} · '
                    f'{bill["account_name"] or "No account"}'
                )
                c2.metric("Amount", money(bill["amount"]))
                c3.write("Paid" if bill["paid"] else "Due")

                b1, b2 = st.columns(2)

                if not bill["paid"]:
                    if b1.button(
                        "Record payment",
                        key=f'bill_pay_{bill["id"]}',
                    ):
                        try:
                            db.pay_bill(
                                bill["id"],
                                date.today().isoformat(),
                            )
                            refresh("Bill payment recorded.")
                        except ValueError as error:
                            st.error(str(error))
                else:
                    b1.caption("One-time bill completed.")

                if b2.button(
                    "Delete",
                    key=f'bill_delete_{bill["id"]}',
                ):
                    db.delete_bill(bill["id"])
                    refresh("Bill deleted.")

    with subs_tab:
        subscriptions = db.get_subscriptions()
        st.metric(
            "Estimated monthly subscription cost",
            money(an.monthly_subscription_cost(subscriptions)),
        )

        with st.expander("Add subscription"):
            if not accounts:
                st.info(
                    "Create an account before attaching a subscription payment."
                )
            else:
                with st.form("subscription_form", clear_on_submit=True):
                    name = st.text_input(
                        "Subscription name",
                        placeholder="Music",
                    )
                    amount = st.number_input(
                        "Subscription amount",
                        min_value=0.0,
                        step=50.0,
                    )
                    cycle = st.selectbox("Billing cycle", FREQUENCIES)
                    next_payment = st.date_input(
                        "Next payment",
                        value=date.today(),
                    )
                    account_id = account_select(
                        "Payment account",
                        accounts,
                        key="subscription_account",
                    )
                    category = st.text_input(
                        "Category",
                        value="Subscriptions",
                    )
                    payment_method = st.selectbox(
                        "Payment method",
                        PAYMENT_METHODS,
                    )
                    submitted = st.form_submit_button(
                        "Add subscription",
                        type="primary",
                    )

                if submitted:
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
                        refresh("Subscription added.")

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
                    key=f'sub_toggle_{item["id"]}',
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
# Goals & debt
# ------------------------------------------------------------------

def goals_debt_page():
    page_heading(
        "Turn plans into progress.",
        "Savings goals and debt live together so future money has context.",
        "GOALS & DEBT",
    )

    goals_tab, debt_tab = st.tabs(["Savings goals", "Debt"])

    with goals_tab:
        with st.expander("Create goal"):
            with st.form("goal_form", clear_on_submit=True):
                name = st.text_input(
                    "Goal name",
                    placeholder="Emergency Fund",
                )
                target = st.number_input(
                    "Target amount",
                    min_value=0.0,
                    step=1000.0,
                )
                saved = st.number_input(
                    "Already saved",
                    min_value=0.0,
                    step=1000.0,
                )
                target_date = st.date_input(
                    "Target date",
                    value=date.today() + timedelta(days=180),
                )
                submitted = st.form_submit_button(
                    "Add goal",
                    type="primary",
                )

            if submitted:
                if not name.strip() or target <= 0:
                    st.error("Enter a goal name and target.")
                else:
                    db.add_goal(
                        name.strip(),
                        target,
                        saved,
                        target_date.isoformat(),
                    )
                    refresh("Goal created.")

        goals = db.get_goals()

        if not goals:
            st.info("No savings goals yet.")

        for goal in goals:
            progress_card(
                goal["name"],
                goal["saved_amount"],
                goal["target_amount"],
                goal["target_date"] or "No target date",
            )

            c1, c2, c3 = st.columns([2, 1, 1])
            new_saved = c1.number_input(
                f'Update {goal["name"]}',
                min_value=0.0,
                value=float(goal["saved_amount"]),
                step=500.0,
                key=f'goal_value_{goal["id"]}',
            )

            if c2.button(
                "Update",
                key=f'goal_update_{goal["id"]}',
            ):
                db.update_goal_saved(goal["id"], new_saved)
                refresh("Goal updated.")

            if c3.button(
                "Delete",
                key=f'goal_delete_{goal["id"]}',
            ):
                db.delete_goal(goal["id"])
                refresh("Goal deleted.")

    with debt_tab:
        accounts = account_map()

        with st.expander("Add debt"):
            with st.form("debt_form", clear_on_submit=True):
                name = st.text_input(
                    "Debt name",
                    placeholder="Education Loan",
                )
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
                submitted = st.form_submit_button(
                    "Add debt",
                    type="primary",
                )

            if submitted:
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

        if not debts:
            st.info("No standalone debt yet.")

        for debt in debts:
            paid = max(
                float(debt["total_amount"]) - float(debt["remaining_amount"]),
                0,
            )

            progress_card(
                debt["name"],
                paid,
                debt["total_amount"],
                f'{money(debt["remaining_amount"])} remaining · '
                f'{debt["interest_rate"]:.2f}% interest',
            )

            with st.expander(f'Payment · {debt["name"]}'):
                if not accounts:
                    st.info("Create an account before recording a debt payment.")
                else:
                    with st.form(f'debt_payment_{debt["id"]}'):
                        c1, c2 = st.columns(2)
                        principal = c1.number_input(
                            "Principal",
                            min_value=0.0,
                            step=500.0,
                            key=f'principal_{debt["id"]}',
                        )
                        interest = c2.number_input(
                            "Interest",
                            min_value=0.0,
                            step=100.0,
                            key=f'interest_{debt["id"]}',
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
                        pay = st.form_submit_button(
                            "Record debt payment",
                            type="primary",
                        )

                    if pay:
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
    page_heading(
        "Patterns, not noise.",
        "Use your own ledger to understand spending, cash flow and account distribution.",
        "INSIGHTS",
    )

    tx = tx_frame()

    if tx.empty:
        st.info("Add transactions first.")
        return

    numbers = an.overview(tx, report_month)

    metrics(
        [
            (
                "Transactions",
                str(numbers["transaction_count"]),
                "Entries in the selected month.",
            ),
            (
                "Average expense",
                money(numbers["average_expense"]),
                "Mean expense size in the selected month.",
            ),
            (
                "Largest expense",
                money(numbers["largest_amount"]),
                numbers["largest_expense"] or "No expenses yet.",
            ),
            (
                "Savings rate",
                "—"
                if numbers["savings_rate"] is None
                else f'{numbers["savings_rate"]:.1f}%',
                "Net cash flow divided by income.",
            ),
        ]
    )

    left, right = st.columns(2)

    with left:
        st.subheader("Category spending")
        category = an.category_spending(tx, report_month)

        if category.empty:
            st.caption("No expense data for this month.")
        else:
            category_chart = (
                alt.Chart(category)
                .mark_bar(
                    color=MINT,
                    cornerRadiusTopLeft=4,
                    cornerRadiusTopRight=4,
                )
                .encode(
                    x=alt.X("amount:Q", title="₹"),
                    y=alt.Y(
                        "category:N",
                        sort="-x",
                        title=None,
                    ),
                    tooltip=["category", "amount"],
                )
                .properties(height=300)
            )
            st.altair_chart(
                category_chart,
                use_container_width=True,
            )

    with right:
        st.subheader("Daily spending")
        daily = an.daily_spending(tx, report_month)

        if daily.empty:
            st.caption("No expense data for this month.")
        else:
            daily_chart = (
                alt.Chart(daily)
                .mark_area(
                    color=GOLD,
                    opacity=0.22,
                    line={"color": GOLD, "strokeWidth": 2},
                )
                .encode(
                    x=alt.X("date:T", title=None),
                    y=alt.Y("amount:Q", title="₹"),
                    tooltip=["date", "amount"],
                )
                .properties(height=300)
            )
            st.altair_chart(
                daily_chart,
                use_container_width=True,
            )

    st.subheader("Monthly cash flow")
    monthly = an.monthly_cash_flow(tx)
    chart = cash_flow_chart(monthly)

    if chart is not None:
        st.altair_chart(chart, use_container_width=True)

    if not monthly.empty:
        shown = monthly.copy()
        for column in [
            "income",
            "expenses",
            "net",
            "three_month_avg_expenses",
        ]:
            shown[column] = shown[column].map(money)
        st.dataframe(
            shown,
            hide_index=True,
            use_container_width=True,
        )

    st.subheader("Account distribution")
    distribution = an.account_distribution(db.get_accounts(), tx)

    if distribution.empty:
        st.caption("No account data.")
    else:
        dist_chart = (
            alt.Chart(distribution)
            .mark_bar(color=MINT)
            .encode(
                x=alt.X("balance:Q", title="Balance"),
                y=alt.Y("name:N", sort="-x", title=None),
                tooltip=["name", "balance"],
            )
            .properties(height=260)
        )
        st.altair_chart(dist_chart, use_container_width=True)


# ------------------------------------------------------------------
# Planning
# ------------------------------------------------------------------

def planning_page():
    page_heading(
        "See the month before it disappears.",
        "Review what happened, then look forward to the next commitments and recurring entries.",
        "PLANNING",
    )

    tx = tx_frame()
    numbers = an.overview(tx, report_month)

    st.subheader("Monthly review")
    metrics(
        [
            (
                "Cash flow",
                money(numbers["net"]),
                "Income minus expenses.",
            ),
            (
                "Top category",
                numbers["top_category"] or "—",
                "Highest-spending category.",
            ),
            (
                "Largest expense",
                numbers["largest_expense"] or "—",
                money(numbers["largest_amount"]),
            ),
            (
                "Transactions",
                str(numbers["transaction_count"]),
                "Entries recorded this month.",
            ),
        ]
    )

    if numbers["income"] == 0 and numbers["expenses"] == 0:
        st.info("No monthly activity to review yet.")
    else:
        if numbers["net"] >= 0:
            st.success(
                f"You finished the month with {money(numbers['net'])} "
                "of positive cash flow."
            )
        else:
            st.warning(
                f"Expenses exceeded income by "
                f"{money(abs(numbers['net']))}."
            )

    st.subheader("Timeline")
    timeline = an.timeline(
        db.get_bills(),
        db.get_subscriptions(),
        db.get_goals(),
        db.get_recurring_entries(),
    )

    if timeline.empty:
        st.info("No upcoming commitments or targets.")
    else:
        days = st.slider(
            "Days ahead",
            min_value=14,
            max_value=180,
            value=60,
            step=7,
        )
        start = pd.Timestamp(date.today())
        end = start + pd.Timedelta(days=days)
        shown = timeline[
            (timeline["date"] >= start)
            & (timeline["date"] <= end)
        ].copy()

        if shown.empty:
            st.caption("Nothing scheduled in this window.")
        else:
            shown["date"] = shown["date"].dt.date
            shown["amount"] = shown["amount"].map(money)
            st.dataframe(
                shown[["date", "type", "name", "amount", "status"]],
                hide_index=True,
                use_container_width=True,
            )

    st.subheader("Recurring generation")
    c1, c2 = st.columns([1, 2])
    until = c1.date_input(
        "Generate through",
        value=date.today(),
        key="planning_generate_until",
    )

    if c2.button(
        "Generate due recurring transactions",
        type="primary",
    ):
        created = db.generate_due_recurring(until.isoformat())
        refresh(f"Generated {created} recurring transaction(s).")


# ------------------------------------------------------------------
# Data & settings
# ------------------------------------------------------------------

def data_settings_page():
    page_heading(
        "Your data stays portable.",
        "Load demo records, move transactions with CSV, or keep a complete local backup.",
        "DATA & SETTINGS",
    )

    st.subheader("Demo workspace")
    st.write(
        "Load fictional records to explore FYNTRA without entering "
        "everything manually."
    )

    if st.button("Load demo data", type="primary"):
        try:
            load_sample_data()
            refresh("Demo data loaded.")
        except ValueError as error:
            st.error(str(error))

    st.divider()

    st.subheader("Transactions CSV")

    c1, c2 = st.columns(2)

    c1.download_button(
        "Download transactions.csv",
        data=csv_tools.transactions_csv(),
        file_name="fyntra_transactions.csv",
        mime="text/csv",
        use_container_width=True,
    )

    c2.download_button(
        "Download import template",
        data=csv_tools.transaction_template_csv(),
        file_name="fyntra_transaction_template.csv",
        mime="text/csv",
        use_container_width=True,
    )

    uploaded_csv = st.file_uploader(
        "Import transactions CSV",
        type=["csv"],
    )

    if uploaded_csv is not None:
        if st.button("Import CSV"):
            try:
                count = csv_tools.import_transactions(
                    uploaded_csv.getvalue()
                )
                refresh(f"Imported {count} transaction(s).")
            except (ValueError, TypeError) as error:
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
        "Restore full backup ZIP",
        type=["zip"],
    )

    confirm_restore = st.checkbox(
        "I understand restore replaces current local FYNTRA data.",
        key="restore_confirm",
    )

    if backup is not None and st.button(
        "Restore backup",
        disabled=not confirm_restore,
    ):
        try:
            count = csv_tools.restore_bundle(backup.getvalue())
            refresh(f"Backup restored. {count} records loaded.")
        except Exception as error:
            st.error(str(error))

    st.divider()

    st.subheader("Local database")
    st.caption(
        "FYNTRA currently uses SQLite. The database file stays on this "
        "computer when you run the app locally."
    )

    st.warning("Reset permanently deletes all local FYNTRA data.")
    confirm_delete = st.checkbox(
        "I understand that all local data will be deleted.",
        key="delete_confirm",
    )

    if st.button(
        "Delete all data",
        disabled=not confirm_delete,
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
    "Data & Settings": data_settings_page,
}

PAGES[page]()
