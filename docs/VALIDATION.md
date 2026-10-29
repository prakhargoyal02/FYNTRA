# Validation record

## Automated checks

FYNTRA includes finance, interface and cloud-boundary regression tests covering money conversion, transfer neutrality, budget status boundaries, empty-state analytics, bill and subscription payment safety, debt payment and undo, anchored recurrence, CSV round trips, duplicate handling, rollback, session isolation, statement parsing/import flows and transaction CRUD through Streamlit AppTest.

GitHub Actions runs the full test suite on Python 3.12 and Python 3.13.

## Interface review

The current desktop and mobile layouts use fictional demo data. Cards recompose on smaller screens, charts follow container width and detailed tables retain internal scrolling where needed.

![Desktop preview](../assets/clarity-desktop.jpg)

<img src="../assets/clarity-mobile.jpg" alt="FYNTRA mobile overview with fictional data" width="320" />

## Cloud boundary

FYNTRA cloud tables use Row Level Security. Ownership policies constrain reads, inserts, updates and deletes to the authenticated user ID. Private mode uses a temporary SQLite working copy and revision guards to prevent silent cloud overwrites.

## Deployment

The public FYNTRA demo is available at https://fyntra-prakhargoyal-0003.streamlit.app. The deployed demo uses fictional data and does not require private cloud credentials.

Automated checks cover financial rules, data processing and Streamlit route behavior. Browser-level deployment checks should be repeated after dependency, authentication, deployment or major interface changes.
