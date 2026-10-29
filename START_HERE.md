# FYNTRA / Clarity redesign

## Open in VS Code

1. Extract the full ZIP to a writable folder.
2. Install Python 3.12 or 3.13. Enable the Python launcher or add Python to PATH.
3. Double-click `START_FYNTRA.cmd`. The first run installs the pinned dependencies and requires internet.
4. Open http://localhost:8501. The fictional demo needs no credentials.
5. Open `FYNTRA.code-workspace` in VS Code. Select `.venv/Scripts/python.exe` with **Python: Select Interpreter**; press F5 to debug. Stop the standalone launcher first so it does not occupy the same port.

`DIAGNOSE_FYNTRA.cmd` writes an environment report to `logs/diagnostics.txt`. The local launcher does not publish changes to your live website.

## Terminal

```powershell
py -3.13 tools/manage.py setup
.venv\Scripts\python.exe tools/manage.py run
.venv\Scripts\python.exe tools/manage.py doctor
.venv\Scripts\python.exe tools/manage.py test
```

Use `py -3.12` for Python 3.12. On macOS/Linux use `python3 tools/manage.py setup`, then `.venv/bin/python` for the remaining commands. Windows was tested; macOS/Linux were not directly tested.

No virtual-environment activation or PowerShell policy change is needed. If port 8501 is occupied, use `tools/manage.py run --port 8502`. If a restricted coding environment cannot write temporary files, ask that environment to provide a writable TEMP/TMP location within its allowed workspace.

## Your data

Public demo changes are temporary: export a FYNTRA Bundle before closing the session to keep them. Private mode requires your own Supabase URL and publishable key using `.streamlit/secrets.toml.example`. Never use a service-role key. No private records, real statements or credentials are included in this package.

## Continue with another AI

Read `AI_START_HERE.md` and give the assistant access to this extracted folder. The application is ordinary editable Python; it needs no AI subscription or API key. Each assistant still uses its own file permissions and tools.

See `docs/REDESIGN.md` for the design decisions and verification evidence. Source history is available in https://github.com/prakhargoyal02/FYNTRA.
