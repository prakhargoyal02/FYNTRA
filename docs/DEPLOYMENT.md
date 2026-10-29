# Deployment and private workspace setup

## Streamlit Community Cloud

1. Push this repository to GitHub.
2. At https://share.streamlit.io, choose Create app and deploy an existing GitHub repository.
3. Select `prakhargoyal02/FYNTRA`, branch `main`, entrypoint `app.py`.
4. In Advanced settings, choose Python 3.13 (3.12 is also supported). No external database is needed for the public fictional demo.
5. For private login and saved statement analysis, add the Supabase configuration below to the app's secrets settings.
6. Verify the signed-out fictional demo, transaction entry, backup export and a fresh-browser session. Then verify private login with an existing test/owner account.

See the official Streamlit deployment and secrets documentation for current hosting steps.

## Supabase

Use a project you control. Review and apply `supabase_schema.sql` once. It creates the FYNTRA-owned cloud tables:

- `public.fyntra_state` for the versioned private workspace snapshot.
- `public.fyntra_statements` for saved bank-statement analysis.

Both tables use Row Level Security so authenticated users can access only rows they own. Anonymous users have no table grants.

Configure an existing Supabase email/password user through your project's normal account-management process. FYNTRA does not provide public registration or password recovery in v1. Never use a banking password. Never send credentials in source files or screenshots.

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` locally, or paste its structure into Streamlit Community Cloud's secrets editor:

```toml
[supabase]
url = "https://YOUR_PROJECT.supabase.co"
publishable_key = "sb_publishable_YOUR_KEY"
```

A legacy anon JWT also works. Service-role or secret keys must not be used. Environment alternatives are `FYNTRA_SUPABASE_URL` and `FYNTRA_SUPABASE_KEY`.

## Operational behavior

Private FYNTRA state is synchronized as a versioned JSON bundle with a 5 MB state limit. SQLite remains the relational working store. Cloud writes compare the last loaded revision; a competing update produces a conflict instead of silently overwriting newer data.

Saved bank-statement rows are stored separately in `fyntra_statements`. Importing reviewed statement rows into the FYNTRA ledger is an explicit action; saved statement analysis and ledger transactions remain separate.

Each browser session owns a temporary SQLite database. A server restart destroys unsynced working data, while successful private cloud saves persist. Do not depend on the Streamlit Community Cloud filesystem for durable personal records. Keep exported FYNTRA backups somewhere private.

The default refresh token lives in browser session storage. Remember opts into local storage. Sign out clears the local browser tokens and attempts server revocation. With no configured cloud credentials, only the isolated fictional demo is available.

## Release verification

Run `python -m pytest -q`. Check both desktop and phone widths. Verify anonymous data isolation, linked-payment undo, recurring duplicate guards, FYNTRA backup restoration, bank-statement import behavior and empty private state. Use `docs/VALIDATION.md` to distinguish automated and interface checks.
