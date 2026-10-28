# Technology learning map

## Follow one transaction

1. `views.transaction_form` gathers a date, rupee amount and account.
2. `database.money` converts the decimal amount into integer paise.
3. `Store.save` normalizes columns, checks relationships and writes parameterized SQL.
4. `analytics.transactions_frame` reads a DataFrame and merges account labels.
5. `month_transactions` selects records with `loc` and a parsed month.
6. `category_summary` uses `groupby(...).agg(...)` to sum spending and count entries.
7. `overview` and `budget_summary` calculate the numbers rendered by Streamlit.

## NumPy exercises

- Read the guarded `np.divide` in `budget_summary`. Explain why a zero budget with spending yields infinity but a zero budget with no spending yields zero.
- Trace the prefix sums in `daily_spending`: a trailing window is the difference between two cumulative totals divided by its number of days. Zero-spend days are included.
- Explain how `np.maximum` and `np.minimum` separate assets from liabilities.
- Compare the daily mean with a mean computed only on transaction days. Explain why excluding quiet days overstates the monthly projection.
- Describe the difference between arithmetic extrapolation and machine-learning prediction.

## Pandas exercises

| Concept | Example |
| --- | --- |
| DataFrame and Series | SQLite query result; a selected amount column |
| `to_datetime` | Parsed transaction dates and calendar filters |
| `merge` | Human-readable account names; budget limits joined to spending |
| `loc` / `iloc` | Filter expense rows; select a leading category or snapshot |
| `groupby` / aggregation | Category totals, account inflows and debt principal sums |
| `pivot_table` | Months × income/expense direction |
| `sort_values` / `nlargest` | Ledger sorting; highest spending days |
| `drop_duplicates` | Repeated record IDs in the prospective import state |
| `reindex` | Include months and days without transactions |
| CSV IO | Typed parsing and portable exports |

## Database exercises

Read the transfer CHECK constraint and account foreign keys. Explain why an account with linked transactions cannot simply be deleted. Trace a bill payment and its undo. Explain why a batch import is validated within a transaction rather than inserting each CSV row independently.

## A two-minute interview explanation

“FYNTRA is a personal finance workspace using Python, SQLite, Pandas, NumPy and Streamlit. I keep monetary records in integer paise and derive account balances from the ledger. Pandas handles joins, date filters, grouped totals and pivots; NumPy handles guarded ratios, rolling averages and financial summaries. Transfers are separate from income and expenses. Each visitor has an isolated fictional demo. Optional private login uses Supabase ownership policies and revision checks. The interesting engineering challenges were atomic linked payments, month-end recurrence dates and lossless, duplicate-safe backups.”

Then demonstrate an account transfer, a budget calculation and the CSV round-trip tests. Be clear about what you understand and what you would improve.
