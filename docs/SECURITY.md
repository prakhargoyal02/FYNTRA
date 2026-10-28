# Security and privacy model

## Boundaries

- Demo data is generated fictionally for each session; it is never loaded from an owner's private database.
- SQLite stores use separate temporary directories. No globally cached Store or authenticated client is shared between visitors.
- Supabase RLS restricts each cloud row to its authenticated owner. Application filtering is additional protection, not a substitute for RLS.
- Passwords are transient inputs. No service-role key is accepted or shipped. Publishable/anon keys are deployment configuration.
- User text inserted into custom HTML is escaped. CSV uploads are parsed as data, never executed as SQL, Python or JavaScript.
- CSV formula prefixes are escaped on export. Imports validate a whole candidate state atomically; file and row limits bound resource use.
- SQL values use bound parameters. Dynamic table names are restricted to the schema allowlist.
- Money is integer paise with range checks; foreign keys and domain rules protect related records.

## Limits

This is a portfolio application, not a bank or audited financial service. It does not provide end-to-end encryption, multi-factor login UI, banking integrations, payment execution, automatic interest accrual or disaster-recovery guarantees. Hosting administrators can access stored data. Refresh tokens are bearer credentials accessible to the app's JavaScript; use trusted devices and avoid untrusted custom scripts.

Demo edits and unsynced private edits are temporary. Export before leaving a session with a sync error. Concurrent edits require manual reconciliation. Full-state sync has a 5 MB limit.

Dependencies are pinned for repeatable installation but should receive reviewed security updates over time. Keep Supabase's account protections configured appropriately, including leaked-password checks where available. Never weaken RLS to resolve a sign-in problem.

## Reporting a problem

For public code bugs, open a GitHub issue containing only fictional reproductions. Never attach a personal database, finance bundle, password, access token or refresh token. If a credential is exposed, revoke it using the provider's normal security controls before sharing diagnostic details.
