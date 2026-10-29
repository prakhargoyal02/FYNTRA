import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

os.environ["FYNTRA_TESTING"] = "1"


def test_calculator_supports_arithmetic_and_rejects_code():
    from workspace_tools import calculate

    assert calculate("(12500 + 4200) / 3") == pytest.approx(5566.666666666667)
    assert calculate("1000 * 1.18") == pytest.approx(1180)
    with pytest.raises(ValueError):
        calculate("__import__('os').system('echo nope')")
    with pytest.raises(ValueError):
        calculate("2 ** 99")
    with pytest.raises(ValueError):
        calculate("5 / 0")


def test_existing_account_can_be_selected_and_edited():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
    app.sidebar.radio[0].set_value("Accounts").run()
    assert not app.exception

    action = next(w for w in app.segmented_control if w.label == "Account action")
    action.set_value("Edit existing account").run()
    picker = next(w for w in app.selectbox if w.label == "Existing account")
    account_id = picker.value
    store = app.session_state.store
    original = store.get("accounts", account_id)

    name = next(w for w in app.text_input if w.label == "Account name")
    name.set_value(original["name"] + " edited")
    next(w for w in app.button if w.label == "Update account").click().run()

    assert not app.exception
    assert store.get("accounts", account_id)["name"] == original["name"] + " edited"
