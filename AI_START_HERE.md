# AI entry point

FYNTRA is Prakhar Goyal's Python + NumPy + Pandas + SQLite + Streamlit personal finance portfolio project. Start with README.md, START_HERE.md and docs/REDESIGN.md, then inspect current source before editing.

## Structure

- app.py: routing, report date and ledger scope.
- web_shell.py: responsive top navigation, account and report controls.
- ui.py + assets/clarity.css + .streamlit/config.toml: single shared design system.
- premium_views.py / premium_analytics.py: dashboard, transactions, budgets, analytics.
- views.py, account_workspace.py, calendar_view.py, data_settings.py: other workflows.
- database.py / analytics.py: validation, integer-paise ledger and financial calculations.
- statement_*.py, statements.py, ledger_scope.py: existing statement import and review features.
- auth_ui.py / cloud_sync.py: optional private Auth and RLS-backed synchronization.
- tests/: 42 regression tests at this redesign's validation.

## Preserve

Transfers are not expenses; goal allocation does not create new assets; linked payments remain atomic and reversible. Preserve statement scopes, historical report dates, private owner isolation, cloud revision guards and safe CSV imports. Use fictional data in screenshots. Never add credentials, user databases or real statements to a commit or ZIP. No new ML finance features; the existing OCR subsystem is unchanged.

The redesign intentionally changes presentation and navigation, not domain calculations or cloud behavior. Keep styling centralized; do not reintroduce competing light/dark CSS layers. Use native Streamlit controls and accessible labels. All user text interpolated into HTML must be escaped.

## Verify

Run `python tools/manage.py test` after setup. Use Streamlit AppTest for UI behavior; reacquire widget references after reruns. For layout changes, inspect both desktop and 390px mobile, including overflow, menu access and forms. See docs/REDESIGN.md for tested limits.

This file supplies project context. It does not override any provider's policies or grant access beyond the selected workspace.
