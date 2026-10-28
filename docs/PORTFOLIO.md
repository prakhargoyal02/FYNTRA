# FYNTRA portfolio case study

## Problem and solution

People can record expenses yet still struggle to understand the money available, bills approaching and whether spending fits their plans. FYNTRA joins those questions into a single workspace. The dashboard starts with a concise overview and reveals detail progressively instead of presenting every table at once.

This is my second portfolio project. After PRism established Python, Pandas, SQLite and Streamlit foundations, FYNTRA deliberately deepens numerical reasoning with NumPy and more demanding Pandas transformations. It does not use machine learning or predictive models.

## Architecture and data model

Streamlit handles interaction. Python domain functions validate and apply changes. SQLite holds normalized tables with stable IDs and foreign keys. Pandas reads the tables, joins labels and prepares chart data. NumPy computes vectorized ratios, summaries and rolling values. Optional Supabase authentication and a versioned cloud snapshot preserve private work across devices.

The related tables are profile, accounts, transactions, budgets, recurring_transactions, bills, subscriptions, savings_goals, goal_contributions, debts, debt_payments and net_worth_snapshots. Bills and debt payments reference their generated ledger entries. Transfers identify two accounts and are explicitly excluded from income/expense aggregations.

Cloud storage intentionally contains one validated state bundle per owner rather than a second parallel set of relational tables. This keeps SQLite central to the project and reduces synchronization scope. The tradeoff is whole-state transfer, a 5 MB cloud limit and explicit conflict resolution rather than automatic merging.

## Decisions worth explaining in an interview

- **Integer money:** Decimal rounds user-entered rupees at the boundary; SQLite stores integer paise to avoid accumulating binary floating-point errors. Analytics convert to rupees for display and charts.
- **Derived balances:** account balances are opening balances plus movements. There is no second independently edited balance field to drift from the ledger.
- **Atomic payments:** bill payment, ledger entry and next recurrence are committed together. Failed debt payments cannot partly reduce a balance.
- **Explicit recurrence:** opening a screen never posts payments. Stable occurrence keys and a next-date guard prevent duplicate bill/subscription/recurring entries.
- **Zero denominators:** savings rates with no income show an unavailable value. Spending against a zero category budget is over budget instead of silently becoming zero utilization.
- **Historical honesty:** projections declare their assumptions, and net-worth history contains saved observations rather than fabricated historical values.

## Bugs and edge cases addressed

An early importer used transaction content alone for deduplication. That could collapse two real purchases with identical details during a backup restore. Stable IDs now take precedence; only ID-less external rows use a fingerprint. Tests include two identical purchases with distinct IDs and a full round trip.

Monthly schedules cannot simply add 30 days. A January 31 schedule clips to February's last day and returns to March 31 using a preserved anchor day. Tests cover leap-year clipping.

Counting a transfer as spending would distort cash flow and budgets. Transfers have a separate direction and destination, and the analytics explicitly include them only in account movement calculations.

A zero-income month and an empty private workspace must still render. Guarded division and schema-preserving empty DataFrames handle these cases.

## Design and accessibility

The visual identity uses near-black surfaces, warm ivory, mint and restrained gold. Native controls retain keyboard and focus behavior. Custom HTML is limited to escaped display elements; reduced-motion preferences disable decorative animation.

Numbers use Indian grouping. Cards and form columns stack on phones; charts fit their containers. Tables remain internally scrollable when their full data cannot fit a small screen. A public fictional-data badge distinguishes the demo from a private workspace.

## CSV portability

Pandas detects record types from columns, previews row counts and constructs a candidate whole-state snapshot. Foreign keys and domain checks validate that candidate inside one SQLite transaction. Replacement affects only included types. A rejected batch rolls back all changes. Formula-like strings are escaped in exports without changing their stored meaning.

## Privacy and synchronization

Every session has a separate temporary SQLite file. The app does not globally cache user data or authentication clients. Supabase Auth establishes the user; RLS restricts SELECT, INSERT, UPDATE and DELETE to that user's ID. A compare-and-swap revision prevents silent lost updates across devices. Failed sync prompts an export before cloud reload.

Password values are transient inputs. Browser restoration uses refresh tokens rather than passwords. Tokens remain sensitive and require a trusted device and protection against script injection. This project is not an audited financial institution and does not connect to banking systems.

## What this project demonstrates

A complete Python application lifecycle: data modelling, numerical finance calculations, tabular processing, responsive UI, state isolation, transactional workflows, authentication boundaries, regression testing, documentation and deployment preparation. The strongest interview story is explaining how one user action travels from a Streamlit form to validated SQLite writes, then through Pandas and NumPy to the refreshed dashboard.

## Next version

Budget rollover, more flexible bank-CSV mapping, finer-grained cloud synchronization, richer recurrence editing and read-only household sharing are deliberate future work. More advanced recommendation and prediction techniques are reserved for later projects where they fit the product problem.
