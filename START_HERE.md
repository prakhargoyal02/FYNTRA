# FYNTRA local setup

## Windows quick start

1. Install Python 3.12 or 3.13. Enable the Python launcher or add Python to PATH.
2. Clone or download this repository to a writable folder.
3. Double-click `START_FYNTRA.cmd`. The first run creates `.venv` and installs the pinned dependencies.
4. Open `http://localhost:8501`. The fictional demo needs no credentials.
5. For development, open `FYNTRA.code-workspace` in VS Code and select `.venv/Scripts/python.exe` as the interpreter.

`DIAGNOSE_FYNTRA.cmd` runs the project diagnostics. The local launcher does not publish changes to the hosted Streamlit app.

## Terminal commands

```powershell
py -3.13 tools/manage.py setup
.venv\Scripts\python.exe tools/manage.py run
.venv\Scripts\python.exe tools/manage.py doctor
.venv\Scripts\python.exe tools/manage.py test
```

Use `py -3.12` for Python 3.12. On macOS/Linux, use `python3 tools/manage.py setup`, then `.venv/bin/python` for the remaining commands.

If port 8501 is occupied, run `tools/manage.py run --port 8502`.

## Private workspace

The public demo uses fictional session data. Private mode requires a Supabase URL and publishable key using `.streamlit/secrets.toml.example`. Never use a service-role key.

No private records, real bank statements, passwords or credentials are included in this repository.

For deployment and security details, see `docs/DEPLOYMENT.md` and `docs/SECURITY.md`.
