# Deployment and private workspace setup

## Streamlit Community Cloud

1. Push this repository to GitHub.
2. At https://share.streamlit.io, choose Create app and deploy an existing GitHub repository.
3. Select `prakhargoyal02/FYNTRA`, branch `main`, entrypoint `app.py`.
4. In Advanced settings, choose Python 3.13 (3.12 also supported). No external database is needed for the public demo.
5. For private login, add the Supabase configuration below to the app's secrets settings. Deploy and wait for the app to start.
6. Verify the signed-out fictional demo, transaction entry, CSV export and a fresh-browser session. Then verify private login and refresh with an existing test/owner account.

See the official [deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) and [secrets guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

## Supabase

Use a project you control. Review and apply `supabase_schema.sql` once. It adds only `public.fyntra_state`; it does not modify PRism tables. RLS restricts all operations to `auth.uid() = user_id`, anonymous access has no table grant, and `user_id` references the authenticated user.

Configure an existing Supabase email/password user through your project's normal account-management process. FYNTRA does not provide public registration or password recovery in v1. Never use a banking password. Never send credentials in source files, screenshots or chat.

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` locally, or paste its structure into Community Cloud's secrets editor:

```toml
[supabase]
url = "https://YOUR_PROJECT.supabase.co"
publishable_key = "sb_publishable_YOUR_KEY"
```

A legacy anon JWT also works. Service-role or secret keys must not be used. Environment alternatives are `FYNTRA_SUPABASE_URL` and `FYNTRA_SUPABASE_KEY`.

## Operational behavior

Private data is synced as a versioned JSON bundle, with a 5 MB cloud size limit. SQLite remains the relational working store. Cloud writes compare the last loaded revision; a competing update produces a conflict, not an overwrite. Export the local bundle, reload cloud data, and reconcile deliberately.

Each browser session owns a temporary database; a server restart destroys unsynced working data. Successful private cloud saves persist. Do not depend on the Community Cloud filesystem for durable personal records. Keep exported backups somewhere private.

The default refresh token lives in browser sessionStorage. Remember opts into localStorage. Sign out clears both and attempts server revocation. With no configured cloud credentials, only the isolated demo is available.

## Release verification

Run `python -m pytest -q`. Check both desktop and phone widths. Verify anonymous data isolation, linked payment undo, recurring duplicate guards, complete CSV restoration and empty private state. Use `docs/VALIDATION.md` to distinguish automated, visual and authenticated checks.
