"""Clear account management on top of the existing FYNTRA Store."""
import streamlit as st

import analytics as an
import views
from database import ACCOUNT_TYPES, money
from ui import hero, metrics, rupees, section_header


def _go_transactions():
    st.session_state.page_nav = "Transactions"


def _form(row):
    row = row or {}
    form_key = "account-form-" + str(row.get("id") or "new")
    with st.form(form_key):
        name = st.text_input("Account name", row.get("name", ""))
        account_type = row.get("account_type", "bank")
        if account_type not in ACCOUNT_TYPES:
            account_type = "bank"
        kind = st.selectbox("Account type", ACCOUNT_TYPES, index=ACCOUNT_TYPES.index(account_type))
        opening = st.number_input(
            "Opening balance (₹)",
            value=float(row.get("opening_balance_paise", 0) / 100),
            help="Use this only for the balance on the account's opening date. Add later money through Transactions.",
        )
        opening_date = st.date_input("Opening balance date", views.d(row.get("opening_date")))
        notes = st.text_area("Account notes", row.get("notes", ""))
        submitted = st.form_submit_button(
            "Update account" if row else "Create account",
            type="primary",
            use_container_width=True,
        )
    if submitted:
        values = dict(
            name=name,
            account_type=kind,
            opening_balance_paise=money(opening),
            opening_date=opening_date.isoformat(),
            notes=notes,
        )
        views.save("accounts", row, values)


def accounts_page():
    hero(
        "One view of every account.",
        "Create an account, correct its setup, or jump back to the ledger when money actually moves.",
        "ACCOUNTS",
    )
    store = views.current()
    accounts = an.account_summary(store)

    if accounts.empty:
        st.info("No accounts yet. Create the first one below.")
    else:
        card_columns = st.columns(2, gap="medium")
        for index, row in enumerate(accounts.to_dict("records")):
            with card_columns[index % 2]:
                with st.container(border=True, key=f"account-card-{row['id']}"):
                    st.caption(str(row["account_type"]).replace("_", " ").upper())
                    st.subheader(row["name"])
                    st.metric("Balance", rupees(row["balance"]))
                    flow_left, flow_right = st.columns(2)
                    flow_left.metric("Inflow", rupees(row["inflow_paise"] / 100))
                    flow_right.metric("Outflow", rupees(row["outflow_paise"] / 100))
                    st.caption("Latest activity: " + str(row["last_activity"]))

    section_header(
        "Manage an account",
        "Choose exactly what you want to do. Editing changes the account setup; adding money belongs in Transactions.",
    )
    has_accounts = not store.frame("accounts").empty
    actions = ["Create new account"] + (["Edit existing account"] if has_accounts else [])
    action = st.segmented_control(
        "Account action",
        actions,
        default="Edit existing account" if has_accounts else "Create new account",
        key="account-action",
    )

    if action == "Edit existing account" and has_accounts:
        frame = store.frame("accounts")
        labels = frame.set_index("id").name.to_dict()
        account_id = st.selectbox(
            "Existing account",
            list(labels),
            format_func=labels.get,
            key="account-edit-picker",
            help="Pick the account you want to update.",
        )
        row = store.get("accounts", account_id)
        st.caption("Editing the opening balance changes the starting baseline. It does not record a new deposit or payment.")
        _form(row)
        st.caption("Need to remove an account? Data & settings checks linked transactions first so nothing gets orphaned.")
    else:
        _form({})

    with st.container(border=True, key="account-money-movement-help"):
        st.write("**Want to add money to an existing account?**")
        st.caption("Record an income transaction or transfer. That keeps the balance history correct instead of rewriting the opening balance.")
        st.button(
            "Open Transactions",
            key="account-open-transactions",
            type="primary",
            on_click=_go_transactions,
        )

    st.caption(
        "Credit cards use negative balances for amounts owed. A card repayment is a transfer to that account. "
        "Investment balances are manually maintained; market prices are not fetched."
    )
