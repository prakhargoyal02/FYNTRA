"""Shared Streamlit workflows used by the current FYNTRA pages."""
from datetime import date, datetime
import sqlite3

import pandas as pd
import streamlit as st

import analytics as an
from database import FREQUENCIES, money, today
from ui import hero, metrics, progress_card, rupees


def current():
    return st.session_state.store


def month():
    return st.session_state.report_month


def d(value=None):
    return date.fromisoformat(str(value)[:10]) if value else today()


def commit_action(fn, message="Saved"):
    try:
        fn()
        an.take_snapshot(current())
    except (ValueError, sqlite3.Error, KeyError, TypeError) as exc:
        st.error(str(exc))
        return

    cloud = st.session_state.get("cloud")
    if cloud:
        try:
            cloud.push(current())
            st.session_state.pop("sync_error", None)
        except Exception:
            st.session_state.sync_error = (
                "Saved in this session; cloud sync failed or another session changed your data. "
                "Export a backup in Data & settings before reloading."
            )
    st.session_state.notice = message
    st.rerun()


def table(frame):
    st.dataframe(frame, hide_index=True, width="stretch")


def account_select(label="Account", value=None, key=None):
    accounts = current().frame("accounts")
    if accounts.empty:
        st.info("Create an account first in Accounts.")
        st.stop()
    labels = accounts.set_index("id").name.to_dict()
    options = list(labels)
    return st.selectbox(
        label,
        options,
        index=options.index(value) if value in options else 0,
        format_func=labels.get,
        key=key,
    )


def picker(table_name, label="Create or edit", name="name", key=None):
    frame = current().frame(table_name)
    labels = {
        row["id"]: str(row.get(name, row["id"]))
        for row in frame.to_dict("records")
    }
    selected = st.selectbox(
        label,
        [None] + list(labels),
        format_func=lambda value: "New record" if value is None else labels[value],
        key=key or table_name + "-picker",
    )
    return current().get(table_name, selected) if selected else {}


def deletion(table_name, row):
    if row and st.checkbox(
        "Confirm deletion", key=table_name + row["id"] + "confirm"
    ):
        if st.button("Delete record", key=table_name + row["id"] + "delete"):
            commit_action(
                lambda: current().delete(table_name, row["id"]),
                "Deleted",
            )


def save(table_name, row, values):
    if row:
        values["id"] = row["id"]
    commit_action(lambda: current().save(table_name, values))


def transaction_form(row=None):
    row = row or {}
    if row.get("source_type"):
        st.info(
            "This entry is linked to a payment or recurring schedule. "
            "Undo it here before changing its source."
        )
        if st.button("Undo linked payment"):
            commit_action(
                lambda: current().undo_payment(row["id"]),
                "Payment undone",
            )
        return

    direction = st.segmented_control(
        "Direction",
        ["expense", "income", "transfer"],
        default=row.get("kind", "expense"),
        key="tx-kind-" + row.get("id", "new"),
        selection_mode="single",
    ) or "expense"

    with st.form("transaction-" + row.get("id", "new")):
        left, right = st.columns(2)
        on = left.date_input("Date", value=d(row.get("date")))
        at = right.time_input(
            "Time",
            value=datetime.strptime(row.get("time", "12:00"), "%H:%M").time(),
        )
        amount = st.number_input(
            "Amount (₹)",
            min_value=0.01,
            value=float(row.get("amount_paise", 10000) / 100),
            step=100.0,
        )
        account = account_select(value=row.get("account_id"))
        destination = (
            account_select("To account", row.get("to_account_id"))
            if direction == "transfer"
            else None
        )
        category = st.text_input(
            "Category",
            row.get("category", "Transfer" if direction == "transfer" else "Food"),
            help="Use any category name; match your budget category spelling.",
        )
        subcategory = st.text_input("Subcategory", row.get("subcategory", ""))
        merchant = st.text_input("Merchant / source", row.get("merchant", ""))
        methods = ["UPI", "Card", "Cash", "Bank transfer", "Other"]
        existing_method = row.get("payment_method", "Other")
        method = st.selectbox(
            "Payment method",
            methods,
            index=methods.index(existing_method) if existing_method in methods else 4,
        )
        tags = st.text_input("Tags (comma separated)", row.get("tags", ""))
        notes = st.text_area("Notes", row.get("notes", ""))
        submitted = st.form_submit_button(
            "Save transaction", type="primary", width="stretch"
        )

    if submitted:
        save(
            "transactions",
            row,
            dict(
                date=on.isoformat(),
                time=at.strftime("%H:%M"),
                amount_paise=money(amount),
                kind=direction,
                category=category,
                subcategory=subcategory,
                account_id=account,
                to_account_id=destination,
                merchant=merchant,
                payment_method=method,
                tags=tags,
                notes=notes,
            ),
        )

    if row:
        if st.button("Duplicate transaction"):
            clone = {key: value for key, value in row.items() if key != "id"}
            commit_action(
                lambda: current().save("transactions", clone),
                "Transaction duplicated",
            )
        deletion("transactions", row)


def commitments_page():
    hero(
        "Nothing slips past you.",
        "Track renewals, upcoming bills and the payments you have recorded.",
        "BILLS & SUBSCRIPTIONS",
    )
    mode = st.segmented_control(
        "Commitment type", ["Bills", "Subscriptions"], default="Bills"
    )
    is_bill = mode != "Subscriptions"
    table_name = "bills" if is_bill else "subscriptions"
    frame = current().frame(table_name)

    if not is_bill:
        totals = an.subscription_summary(current())
        metrics(
            [
                ("Monthly equivalent", rupees(totals["monthly_cost"]), "Active subscriptions only."),
                ("Yearly equivalent", rupees(totals["yearly_cost"]), "Weekly uses 52 payments per year."),
                ("Next renewal", totals["next_renewal"] or "—", "Next recorded renewal."),
                ("Largest monthly cost", totals["most_expensive"] or "—", "Compared using monthly equivalents."),
            ]
        )
    else:
        status = st.selectbox(
            "Bill status", ["All", "Upcoming", "Due today", "Overdue", "Paid"]
        )
        frame["status"] = (
            frame.apply(
                lambda record: (
                    "Paid"
                    if record.paid
                    else "Overdue"
                    if record.due_date < today().isoformat()
                    else "Due today"
                    if record.due_date == today().isoformat()
                    else "Upcoming"
                ),
                axis=1,
            )
            if not frame.empty
            else pd.Series(dtype=str)
        )
        if status != "All":
            frame = frame.loc[frame.status.eq(status)]

    sort_field = "due_date" if is_bill else "next_date"
    for record in frame.sort_values(sort_field).to_dict("records"):
        with st.container(border=True):
            st.write(f'**{record["name"]}** · {rupees(record["amount_paise"] / 100)}')
            status_text = (
                record["status"]
                if is_bill
                else "Active"
                if record["active"]
                else "Cancelled"
            )
            st.caption(
                f'{record[sort_field]} · {record["frequency"]} · {status_text}'
            )
            if (is_bill and not record["paid"]) or (
                not is_bill and record["active"]
            ):
                if st.button("Record payment today", key="pay" + record["id"]):
                    if is_bill:
                        commit_action(
                            lambda record=record: current().pay_bill(
                                record["id"], today().isoformat()
                            ),
                            "Bill paid",
                        )
                    else:
                        commit_action(
                            lambda record=record: current().pay_subscription(
                                record["id"],
                                today().isoformat(),
                                record["next_date"],
                            ),
                            "Renewal recorded",
                        )

    with st.expander("Create or edit " + ("bill" if is_bill else "subscription")):
        row = picker(table_name)
        if row.get("paid"):
            st.info("Undo the payment in Transactions before editing this paid bill.")
            return
        with st.form("commitment"):
            name = st.text_input("Name", row.get("name", ""))
            amount = st.number_input(
                "Amount (₹)",
                min_value=0.01,
                value=float(row.get("amount_paise", 100000) / 100),
            )
            frequencies = FREQUENCIES if is_bill else FREQUENCIES[1:]
            frequency = st.selectbox(
                "Frequency",
                frequencies,
                index=frequencies.index(row.get("frequency", "monthly")),
            )
            on = st.date_input(
                "Due date" if is_bill else "Next renewal",
                d(row.get("due_date" if is_bill else "next_date")),
            )
            account = account_select(value=row.get("account_id"))
            category = st.text_input(
                "Category",
                row.get("category", "Utilities" if is_bill else "Subscriptions"),
            )
            active = (
                st.checkbox("Active", bool(row.get("active", 1)))
                if not is_bill
                else None
            )
            notes = st.text_area("Notes", row.get("notes", ""))
            submitted = st.form_submit_button("Save commitment", type="primary")

        if submitted:
            values = dict(
                name=name,
                amount_paise=money(amount),
                frequency=frequency,
                anchor_day=on.day,
                account_id=account,
                category=category,
                notes=notes,
            )
            values["due_date" if is_bill else "next_date"] = on.isoformat()
            if not is_bill:
                values["active"] = int(active)
            save(table_name, row, values)
        deletion(table_name, row)

    st.caption(
        "Payment buttons record money already paid; they never charge an account. "
        "Avoid creating a second recurring schedule for the same bill or subscription."
    )


def goals_page():
    hero(
        "Make room for what matters.",
        "Track purposeful savings and see debt coming down.",
        "GOALS & DEBT",
    )
    mode = st.segmented_control(
        "Planning view", ["Savings goals", "Debt"], default="Savings goals"
    )

    if mode != "Debt":
        goals = an.goal_summary(current())
        st.caption(
            "Goals earmark money already in your accounts. Contributions do not move cash or increase net worth; "
            "record a separate transfer if money actually moves."
        )
        for record in goals.to_dict("records"):
            progress_card(
                record["name"],
                record["saved"],
                record["target"],
                f'{rupees(record["remaining"])} left · {record["target_date"]}',
            )

        with st.expander("Create or edit goal"):
            row = picker("savings_goals")
            with st.form("goal"):
                name = st.text_input("Goal name", row.get("name", ""))
                target = st.number_input(
                    "Target (₹)",
                    min_value=0.01,
                    value=float(row.get("target_paise", 10000000) / 100),
                )
                initial = st.number_input(
                    "Already saved before tracking (₹)",
                    min_value=0.0,
                    value=float(row.get("initial_saved_paise", 0) / 100),
                )
                on = st.date_input("Target date", d(row.get("target_date")))
                notes = st.text_area("Goal notes", row.get("notes", ""))
                submitted = st.form_submit_button("Save goal", type="primary")
            if submitted:
                save(
                    "savings_goals",
                    row,
                    dict(
                        name=name,
                        target_paise=money(target),
                        initial_saved_paise=money(initial),
                        target_date=on.isoformat(),
                        notes=notes,
                    ),
                )
            deletion("savings_goals", row)

        if not goals.empty:
            with st.expander("Add or edit a contribution"):
                row = picker("goal_contributions", name="date")
                with st.form("contribution"):
                    labels = goals.set_index("id").name.to_dict()
                    ids = list(labels)
                    goal = st.selectbox(
                        "Goal",
                        ids,
                        index=ids.index(row["goal_id"]) if row else 0,
                        format_func=labels.get,
                    )
                    on = st.date_input("Contribution date", d(row.get("date")))
                    amount = st.number_input(
                        "Contribution (₹)",
                        min_value=0.01,
                        value=float(row.get("amount_paise", 100000) / 100),
                    )
                    notes = st.text_input(
                        "Contribution note", row.get("notes", "")
                    )
                    submitted = st.form_submit_button(
                        "Save contribution", type="primary"
                    )
                if submitted:
                    save(
                        "goal_contributions",
                        row,
                        dict(
                            goal_id=goal,
                            date=on.isoformat(),
                            amount_paise=money(amount),
                            notes=notes,
                        ),
                    )
                deletion("goal_contributions", row)
        return

    debts = an.debt_summary(current())
    st.caption(
        "Track standalone loans here. Card balances already recorded in Accounts must not be entered twice. "
        "Interest is entered when paid; no automatic interest accrual is assumed."
    )
    metrics(
        [
            ("Debt remaining", rupees(debts.remaining.sum()), "Standalone debts only."),
            (
                "Principal repaid",
                rupees((debts.original_paise / 100 - debts.remaining).sum()),
                "Includes repayments before tracking began.",
            ),
        ]
    )
    for record in debts.to_dict("records"):
        progress_card(
            record["name"],
            record["original_paise"] / 100 - record["remaining"],
            record["original_paise"] / 100,
            f'{rupees(record["remaining"])} remaining',
        )

    with st.expander("Create or edit debt"):
        row = picker("debts")
        with st.form("debt"):
            name = st.text_input("Debt name", row.get("name", ""))
            kind = st.text_input("Debt type", row.get("debt_type", "Personal loan"))
            original = st.number_input(
                "Original amount (₹)",
                min_value=0.01,
                value=float(row.get("original_paise", 10000000) / 100),
            )
            remaining = st.number_input(
                "Balance when tracking started (₹)",
                min_value=0.0,
                value=float(row.get("opening_remaining_paise", 10000000) / 100),
            )
            rate = st.number_input(
                "Annual interest rate (%) — optional",
                min_value=0.0,
                max_value=1000.0,
                value=float(row.get("annual_rate", 0)),
            )
            payment = st.number_input(
                "Scheduled monthly payment (₹)",
                min_value=0.0,
                value=float(row.get("monthly_payment_paise", 0) / 100),
            )
            on = st.date_input("Next payment date", d(row.get("next_date")))
            notes = st.text_area("Debt notes", row.get("notes", ""))
            submitted = st.form_submit_button("Save debt", type="primary")
        if submitted:
            save(
                "debts",
                row,
                dict(
                    name=name,
                    debt_type=kind,
                    original_paise=money(original),
                    opening_remaining_paise=money(remaining),
                    annual_rate=rate,
                    monthly_payment_paise=money(payment),
                    next_date=on.isoformat(),
                    notes=notes,
                ),
            )
        deletion("debts", row)

    if not debts.empty:
        with st.expander("Record a debt payment"):
            with st.form("debt-payment"):
                labels = debts.set_index("id").name.to_dict()
                debt = st.selectbox("Debt", list(labels), format_func=labels.get)
                account = account_select()
                principal = st.number_input(
                    "Principal repaid (₹)", min_value=0.01, value=1000.0
                )
                interest = st.number_input(
                    "Interest paid (₹)", min_value=0.0, value=0.0
                )
                on = st.date_input("Paid on", today())
                submitted = st.form_submit_button(
                    "Record debt payment", type="primary"
                )
            if submitted:
                commit_action(
                    lambda: current().pay_debt(
                        debt,
                        account,
                        money(principal),
                        money(interest),
                        on.isoformat(),
                    ),
                    "Debt payment recorded",
                )
        st.caption(
            "Undo a payment from its linked entry in Transactions. "
            "Update the next payment date in the debt editor after payment."
        )


def recurring_page():
    st.subheader("Predictable money movements")
    st.caption(
        "Schedules appear in Calendar. Post due entries explicitly; opening a page never creates transactions. "
        "Do not duplicate bills or subscriptions here."
    )
    frame = current().frame("recurring_transactions")
    table(
        frame[["name", "kind", "amount_paise", "next_date", "frequency", "active"]]
        .assign(amount=lambda data: data.amount_paise / 100)
        .drop(columns="amount_paise")
    )
    if st.button("Post all entries due through today", type="primary"):
        commit_action(
            lambda: current().generate_recurring(today().isoformat()),
            "Due entries posted once",
        )

    row = picker("recurring_transactions")
    directions = ["income", "expense", "transfer"]
    direction = st.selectbox(
        "Recurring direction",
        directions,
        index=directions.index(row.get("kind", "income")),
    )
    with st.form("recurring"):
        name = st.text_input("Schedule name", row.get("name", ""))
        amount = st.number_input(
            "Recurring amount (₹)",
            min_value=0.01,
            value=float(row.get("amount_paise", 100000) / 100),
        )
        account = account_select(value=row.get("account_id"))
        destination = (
            account_select("Destination account", row.get("to_account_id"))
            if direction == "transfer"
            else None
        )
        category = st.text_input("Recurring category", row.get("category", "Salary"))
        frequency = st.selectbox(
            "Repeat",
            FREQUENCIES[1:],
            index=FREQUENCIES[1:].index(row.get("frequency", "monthly")),
        )
        on = st.date_input("Next occurrence", d(row.get("next_date")))
        active = st.checkbox("Schedule active", bool(row.get("active", 1)))
        notes = st.text_area("Schedule notes", row.get("notes", ""))
        submitted = st.form_submit_button("Save schedule", type="primary")

    if submitted:
        save(
            "recurring_transactions",
            row,
            dict(
                name=name,
                kind=direction,
                amount_paise=money(amount),
                account_id=account,
                to_account_id=destination,
                category=category,
                frequency=frequency,
                next_date=on.isoformat(),
                anchor_day=on.day,
                active=int(active),
                notes=notes,
            ),
        )
    deletion("recurring_transactions", row)
