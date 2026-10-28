from datetime import date

import altair as alt
import streamlit as st

import analytics as an
import database as db
from sample_data import load_sample_data

st.set_page_config(page_title="FYNTRA", page_icon="💸", layout="wide")
db.setup_database()


def money(value):
    return f"₹{float(value):,.2f}"


def tx_frame():
    return an.transactions_frame(db.get_transactions())


def account_map():
    return {row["id"]: row["name"] for row in db.get_accounts()}


def refresh(message):
    st.session_state["notice"] = message
    st.rerun()


def heading(title, text):
    st.title(title)
    st.caption(text)


if "notice" in st.session_state:
    st.success(st.session_state.pop("notice"))

st.sidebar.title("FYNTRA")
st.sidebar.caption("Know where your money goes.")
page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Transactions",
        "Accounts",
        "Budgets",
        "Goals",
        "Debts",
        "Bills & Subscriptions",
        "Analytics",
        "Data & Settings",
    ],
)
report_month = st.sidebar.text_input("Report month", value=date.today().strftime("%Y-%m"))


def dashboard_page():
    heading("Dashboard", "Your main money overview.")

    tx = tx_frame()
    overview = an.overview(tx, report_month)
    net_worth = an.total_net_worth(db.get_accounts(), tx, db.get_debts())
    subscription_cost = an.monthly_subscription_cost(db.get_subscriptions())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Income", money(overview["income"]))
    c2.metric("Expenses", money(overview["expenses"]))
    c3.metric("Net cash flow", money(overview["net"]))
    c4.metric("Net worth", money(net_worth))

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Savings rate",
        "—" if overview["savings_rate"] is None else f'{overview["savings_rate"]:.1f}%',
    )
    c2.metric("Average expense", money(overview["average_expense"]))
    c3.metric("Subscriptions / month", money(subscription_cost))

    left, right = st.columns([1.7, 1])

    with left:
        st.subheader("Monthly cash flow")
        monthly = an.monthly_cash_flow(tx)
        if monthly.empty:
            st.info("Add transactions to see the chart.")
        else:
            chart_data = monthly.melt(
                id_vars="month",
                value_vars=["income", "expenses"],
                var_name="type",
                value_name="amount",
            )
            chart = (
                alt.Chart(chart_data)
                .mark_bar()
                .encode(
                    x=alt.X("month:N", title="Month"),
                    xOffset="type:N",
                    y=alt.Y("amount:Q", title="Amount"),
                    color="type:N",
                    tooltip=["month", "type", "amount"],
                )
            )
            st.altair_chart(chart, use_container_width=True)

    with right:
        st.subheader("Top spending categories")
        categories = an.category_spending(tx, report_month)
        if categories.empty:
            st.info("No expenses for this month.")
        else:
            shown = categories.head(6).copy()
            shown["amount"] = shown["amount"].map(money)
            st.dataframe(shown, hide_index=True, use_container_width=True)

    st.subheader("Recent transactions")
    if tx.empty:
        st.info("No transactions yet.")
    else:
        recent = tx.head(8)[
            ["transaction_date", "merchant", "category", "kind", "account_name", "amount"]
        ].copy()
        recent["transaction_date"] = recent["transaction_date"].dt.date
        recent["amount"] = recent["amount"].map(money)
        st.dataframe(recent, hide_index=True, use_container_width=True)


def transactions_page():
    heading("Transactions", "Record income and expenses, then search your history.")
    accounts = account_map()

    if not accounts:
        st.warning("Create an account first.")
        return

    add_tab, history_tab = st.tabs(["Add transaction", "History"])

    with add_tab:
        with st.form("transaction_form", clear_on_submit=True):
            kind = st.selectbox("Type", ["expense", "income"])
            on = st.date_input("Date", value=date.today())
            amount = st.number_input("Amount", min_value=0.01, step=100.0)
            account_id = st.selectbox(
                "Account",
                list(accounts),
                format_func=lambda item: accounts[item],
            )
            category = st.text_input("Category", value="Food" if kind == "expense" else "Salary")
            merchant = st.text_input("Merchant / source")
            notes = st.text_area("Notes")
            saved = st.form_submit_button("Save transaction", type="primary")

        if saved:
            try:
                db.add_transaction(
                    on.isoformat(),
                    kind,
                    amount,
                    account_id,
                    category.strip() or "Other",
                    merchant.strip(),
                    notes.strip(),
                )
                refresh("Transaction saved.")
            except ValueError as error:
                st.error(str(error))

    with history_tab:
        tx = tx_frame()
        if tx.empty:
            st.info("No transactions yet.")
            return

        search = st.text_input("Search", placeholder="Merchant, category, notes...")
        filtered = tx.copy()

        if search:
            text = search.lower()
            filtered = filtered[
                filtered["merchant"].fillna("").str.lower().str.contains(text, regex=False)
                | filtered["category"].fillna("").str.lower().str.contains(text, regex=False)
                | filtered["notes"].fillna("").str.lower().str.contains(text, regex=False)
            ]

        kinds = st.multiselect("Type", ["income", "expense"], default=["income", "expense"])
        filtered = filtered[filtered["kind"].isin(kinds)]

        shown = filtered[
            ["id", "transaction_date", "merchant", "category", "kind", "account_name", "amount"]
        ].copy()
        shown["transaction_date"] = shown["transaction_date"].dt.date
        shown["amount"] = shown["amount"].map(money)
        st.dataframe(shown, hide_index=True, use_container_width=True)

        labels = {
            row["id"]: f'#{row["id"]} | {row["transaction_date"].date()} | '
            f'{row["merchant"] or row["category"]} | {money(row["amount"])}'
            for _, row in filtered.iterrows()
        }
        if labels:
            delete_id = st.selectbox(
                "Delete a transaction",
                list(labels),
                format_func=lambda item: labels[item],
            )
            if st.button("Delete selected transaction"):
                db.delete_transaction(delete_id)
                refresh("Transaction deleted.")


def accounts_page():
    heading("Accounts", "Create the places where your money lives.")

    with st.form("account_form", clear_on_submit=True):
        name = st.text_input("Account name", placeholder="Main Bank")
        account_type = st.selectbox(
            "Account type",
            ["Bank", "Cash", "Wallet", "Credit Card", "Investment"],
        )
        opening = st.number_input("Opening balance", value=0.0, step=500.0)
        saved = st.form_submit_button("Add account", type="primary")

    if saved:
        if not name.strip():
            st.error("Account name is required.")
        else:
            db.add_account(name.strip(), account_type, opening)
            refresh("Account created.")

    accounts = db.get_accounts()
    balances = an.account_balances(accounts, tx_frame())
    if balances.empty:
        st.info("No accounts yet.")
        return

    shown = balances.copy()
    shown["balance"] = shown["balance"].map(money)
    st.dataframe(shown, hide_index=True, use_container_width=True)

    names = {row["id"]: row["name"] for row in accounts}
    account_id = st.selectbox("Delete account", list(names), format_func=lambda item: names[item])
    if st.button("Delete selected account"):
        try:
            db.delete_account(account_id)
            refresh("Account deleted.")
        except ValueError as error:
            st.error(str(error))


def budgets_page():
    heading("Budgets", "Set monthly limits and compare them with real spending.")

    with st.form("budget_form", clear_on_submit=True):
        category = st.text_input("Category", placeholder="Food")
        limit = st.number_input("Monthly limit", min_value=0.0, step=500.0)
        saved = st.form_submit_button("Save budget", type="primary")

    if saved:
        if not category.strip() or limit <= 0:
            st.error("Enter a category and a budget greater than zero.")
        else:
            db.save_budget(category.strip(), limit)
            refresh("Budget saved.")

    status = an.budget_status(db.get_budgets(), tx_frame(), report_month)
    if status.empty:
        st.info("No budgets yet.")
        return

    for _, item in status.iterrows():
        with st.container(border=True):
            st.subheader(item["category"])
            c1, c2, c3 = st.columns(3)
            c1.metric("Limit", money(item["monthly_limit"]))
            c2.metric("Spent", money(item["spent"]))
            c3.metric("Remaining", money(item["remaining"]))
            st.progress(min(max(float(item["used_percent"]) / 100, 0), 1))
            st.caption(f'{item["used_percent"]:.1f}% used')

    budgets = {row["id"]: row["category"] for row in db.get_budgets()}
    budget_id = st.selectbox("Delete budget", list(budgets), format_func=lambda item: budgets[item])
    if st.button("Delete selected budget"):
        db.delete_budget(budget_id)
        refresh("Budget deleted.")


def goals_page():
    heading("Goals", "Track savings goals without complicated rules.")

    with st.form("goal_form", clear_on_submit=True):
        name = st.text_input("Goal name", placeholder="Emergency Fund")
        target = st.number_input("Target amount", min_value=0.0, step=1000.0)
        saved_amount = st.number_input("Already saved", min_value=0.0, step=1000.0)
        target_date = st.date_input("Target date")
        saved = st.form_submit_button("Add goal", type="primary")

    if saved:
        if not name.strip() or target <= 0:
            st.error("Enter a goal name and target greater than zero.")
        else:
            db.add_goal(name.strip(), target, saved_amount, target_date.isoformat())
            refresh("Goal created.")

    goals = db.get_goals()
    if not goals:
        st.info("No goals yet.")
        return

    for goal in goals:
        with st.container(border=True):
            st.subheader(goal["name"])
            target = float(goal["target_amount"])
            current = float(goal["saved_amount"])
            c1, c2, c3 = st.columns(3)
            c1.metric("Saved", money(current))
            c2.metric("Target", money(target))
            c3.metric("Left", money(max(target - current, 0)))
            st.progress(0 if target <= 0 else min(current / target, 1))
            st.caption(f'Target date: {goal["target_date"] or "Not set"}')

            new_value = st.number_input(
                "Update saved amount",
                min_value=0.0,
                value=current,
                step=500.0,
                key=f'goal_value_{goal["id"]}',
            )
            c1, c2 = st.columns(2)
            if c1.button("Update", key=f'goal_update_{goal["id"]}'):
                db.update_goal_saved(goal["id"], new_value)
                refresh("Goal updated.")
            if c2.button("Delete", key=f'goal_delete_{goal["id"]}'):
                db.delete_goal(goal["id"])
                refresh("Goal deleted.")


def debts_page():
    heading("Debts", "Track what you owe and how much is left.")

    with st.form("debt_form", clear_on_submit=True):
        name = st.text_input("Debt name", placeholder="Education Loan")
        total = st.number_input("Original amount", min_value=0.0, step=1000.0)
        remaining = st.number_input("Remaining amount", min_value=0.0, step=1000.0)
        rate = st.number_input("Interest rate %", min_value=0.0, step=0.1)
        saved = st.form_submit_button("Add debt", type="primary")

    if saved:
        if not name.strip() or total <= 0:
            st.error("Enter a debt name and original amount.")
        else:
            db.add_debt(name.strip(), total, remaining, rate)
            refresh("Debt added.")

    debts = db.get_debts()
    if not debts:
        st.info("No debts yet.")
        return

    for debt in debts:
        with st.container(border=True):
            st.subheader(debt["name"])
            c1, c2, c3 = st.columns(3)
            c1.metric("Original", money(debt["total_amount"]))
            c2.metric("Remaining", money(debt["remaining_amount"]))
            c3.metric("Interest", f'{debt["interest_rate"]:.2f}%')

            new_value = st.number_input(
                "Update remaining",
                min_value=0.0,
                value=float(debt["remaining_amount"]),
                step=500.0,
                key=f'debt_value_{debt["id"]}',
            )
            c1, c2 = st.columns(2)
            if c1.button("Update", key=f'debt_update_{debt["id"]}'):
                db.update_debt_remaining(debt["id"], new_value)
                refresh("Debt updated.")
            if c2.button("Delete", key=f'debt_delete_{debt["id"]}'):
                db.delete_debt(debt["id"])
                refresh("Debt deleted.")


def bills_page():
    heading("Bills & Subscriptions", "Keep recurring payments visible.")
    bills_tab, subs_tab = st.tabs(["Bills", "Subscriptions"])

    with bills_tab:
        with st.form("bill_form", clear_on_submit=True):
            name = st.text_input("Bill name")
            amount = st.number_input("Bill amount", min_value=0.0, step=100.0)
            due_date = st.date_input("Due date")
            category = st.text_input("Bill category", value="Bills")
            saved = st.form_submit_button("Add bill")

        if saved:
            if not name.strip() or amount <= 0:
                st.error("Enter a bill name and amount.")
            else:
                db.add_bill(name.strip(), amount, due_date.isoformat(), category.strip() or "Bills")
                refresh("Bill added.")

        for bill in db.get_bills():
            with st.container(border=True):
                st.write(f'**{bill["name"]}** · {money(bill["amount"])}')
                st.caption(f'{bill["due_date"]} · {bill["category"]}')
                paid = bool(bill["paid"])
                c1, c2 = st.columns(2)
                if c1.button(
                    "Mark pending" if paid else "Mark paid",
                    key=f'bill_paid_{bill["id"]}',
                ):
                    db.set_bill_paid(bill["id"], not paid)
                    refresh("Bill updated.")
                if c2.button("Delete", key=f'bill_delete_{bill["id"]}'):
                    db.delete_bill(bill["id"])
                    refresh("Bill deleted.")

    with subs_tab:
        with st.form("subscription_form", clear_on_submit=True):
            name = st.text_input("Subscription name")
            amount = st.number_input("Subscription amount", min_value=0.0, step=50.0)
            cycle = st.selectbox("Billing cycle", ["Monthly", "Weekly", "Yearly"])
            next_payment = st.date_input("Next payment")
            saved = st.form_submit_button("Add subscription")

        if saved:
            if not name.strip() or amount <= 0:
                st.error("Enter a subscription name and amount.")
            else:
                db.add_subscription(name.strip(), amount, cycle, next_payment.isoformat())
                refresh("Subscription added.")

        subscriptions = db.get_subscriptions()
        st.metric("Estimated monthly subscription cost", money(an.monthly_subscription_cost(subscriptions)))

        for item in subscriptions:
            with st.container(border=True):
                st.write(f'**{item["name"]}** · {money(item["amount"])}')
                st.caption(f'{item["billing_cycle"]} · next: {item["next_payment"]}')
                c1, c2 = st.columns(2)
                if c1.button(
                    "Pause" if item["active"] else "Resume",
                    key=f'sub_active_{item["id"]}',
                ):
                    db.set_subscription_active(item["id"], not bool(item["active"]))
                    refresh("Subscription updated.")
                if c2.button("Delete", key=f'sub_delete_{item["id"]}'):
                    db.delete_subscription(item["id"])
                    refresh("Subscription deleted.")


def analytics_page():
    heading("Analytics", "Understand patterns using Pandas and NumPy.")
    tx = tx_frame()
    if tx.empty:
        st.info("Add transactions first.")
        return

    overview = an.overview(tx, report_month)
    categories = an.category_spending(tx, report_month)
    monthly = an.monthly_cash_flow(tx)

    c1, c2, c3 = st.columns(3)
    c1.metric("Transactions this month", overview["transaction_count"])
    c2.metric("Average expense", money(overview["average_expense"]))
    c3.metric(
        "Savings rate",
        "—" if overview["savings_rate"] is None else f'{overview["savings_rate"]:.1f}%',
    )

    st.subheader("Category spending")
    if not categories.empty:
        chart = (
            alt.Chart(categories)
            .mark_bar()
            .encode(
                x=alt.X("amount:Q", title="Amount"),
                y=alt.Y("category:N", sort="-x", title="Category"),
                tooltip=["category", "amount"],
            )
        )
        st.altair_chart(chart, use_container_width=True)

    st.subheader("Net cash-flow trend")
    if not monthly.empty:
        chart = (
            alt.Chart(monthly)
            .mark_line(point=True)
            .encode(
                x=alt.X("month:N", title="Month"),
                y=alt.Y("net:Q", title="Net cash flow"),
                tooltip=["month", "net"],
            )
        )
        st.altair_chart(chart, use_container_width=True)

    shown = monthly.copy()
    for column in ["income", "expenses", "net"]:
        shown[column] = shown[column].map(money)
    st.dataframe(shown, hide_index=True, use_container_width=True)


def settings_page():
    heading("Data & Settings", "Demo data, CSV export and reset tools.")

    st.subheader("Demo data")
    if st.button("Load demo data"):
        try:
            load_sample_data()
            refresh("Demo data loaded.")
        except ValueError as error:
            st.error(str(error))

    st.divider()
    st.subheader("Export transactions")
    tx = tx_frame()

    if tx.empty:
        st.info("There are no transactions to export.")
    else:
        export = tx.copy()
        export["transaction_date"] = export["transaction_date"].dt.strftime("%Y-%m-%d")
        st.download_button(
            "Download transactions.csv",
            data=export.to_csv(index=False).encode("utf-8"),
            file_name="fyntra_transactions.csv",
            mime="text/csv",
        )

    st.divider()
    st.subheader("Reset FYNTRA")
    st.warning("This permanently deletes all local FYNTRA data.")
    confirm = st.checkbox("I understand that all local data will be deleted.")
    if st.button("Delete all data", disabled=not confirm):
        db.clear_all_data()
        refresh("All FYNTRA data deleted.")


PAGES = {
    "Dashboard": dashboard_page,
    "Transactions": transactions_page,
    "Accounts": accounts_page,
    "Budgets": budgets_page,
    "Goals": goals_page,
    "Debts": debts_page,
    "Bills & Subscriptions": bills_page,
    "Analytics": analytics_page,
    "Data & Settings": settings_page,
}

PAGES[page]()
