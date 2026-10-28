import os
from datetime import date
from pathlib import Path

os.environ["FYNTRA_TESTING"] = "1"

from streamlit.testing.v1 import AppTest


def _app():
    return AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "app.py"),
        default_timeout=30,
    ).run()


def test_report_date_and_calendar_range_apply_in_one_rerun():
    app = _app()

    report = next(widget for widget in app.sidebar.date_input if widget.label == "Report date")
    report.set_value(date(2026, 9, 15)).run()
    assert app.session_state.report_date == date(2026, 9, 15)
    assert app.session_state.report_month == "2026-09"

    app.sidebar.radio[0].set_value("Calendar").run()
    timeline_from = next(widget for widget in app.date_input if widget.label == "Timeline from")
    timeline_from.set_value(date(2026, 9, 1)).run()
    assert app.session_state.calendar_timeline_from == date(2026, 9, 1)
    shown = next(widget for widget in app.date_input if widget.label == "Timeline from")
    assert shown.value == date(2026, 9, 1)
    assert not app.exception


def test_statement_scope_applies_after_one_selection(tmp_path):
    from database import Store

    store = Store(tmp_path / "statement-scope.db")
    store.save(
        "accounts",
        dict(id="bank", name="Test Bank", opening_date="2020-01-01"),
    )
    store.save(
        "transactions",
        dict(
            id="sep-row",
            date="2026-09-10",
            amount_paise=100000,
            kind="income",
            account_id="bank",
            category="Salary",
            merchant="September credit",
            notes="Imported from bank statement: September statement",
            source_key="statement:sep:row-1",
        ),
    )
    store.save(
        "transactions",
        dict(
            id="oct-row",
            date="2026-10-10",
            amount_paise=200000,
            kind="income",
            account_id="bank",
            category="Salary",
            merchant="October credit",
            notes="Imported from bank statement: October statement",
            source_key="statement:oct:row-1",
        ),
    )

    app = _app()
    app.session_state.store = store
    app.session_state.mode = "private"
    app.run()

    report = next(widget for widget in app.sidebar.date_input if widget.label == "Report date")
    report.set_value(date(2026, 10, 15)).run()

    ledger = next(widget for widget in app.sidebar.segmented_control if widget.label == "Ledger view")
    ledger.set_value("One statement").run()
    selector = next(widget for widget in app.sidebar.selectbox if widget.label == "Imported statement")
    selector.set_value("oct").run()

    assert app.session_state.statement_scope_id == "oct"
    assert app.session_state.ledger_view == "statement"
    money_in = next(metric for metric in app.metric if metric.label == "Money in")
    assert money_in.value == "₹2,000"
    assert not app.exception
