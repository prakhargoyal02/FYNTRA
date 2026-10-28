"""Compatibility helpers for common bank-export layouts.

The core statement parser stays small and readable. This module widens the
accepted header vocabulary and makes CSV delimiter/header detection more
forgiving without changing ledger rules.
"""
import csv
from io import BytesIO, StringIO
import re

import pandas as pd

import statement_tools as tools

DATE_ALIASES = (
    "transaction date", "txn date", "txn dt", "transaction dt", "date",
    "value date", "posting date", "tran date", "date of transaction",
)
DESCRIPTION_ALIASES = (
    "description", "narration", "particulars", "details", "merchant", "remarks",
    "transaction details", "transaction remarks", "transaction particulars",
    "narrative", "transaction description",
)
DEBIT_ALIASES = (
    "debit", "withdrawal", "withdrawal amount", "withdrawal amt", "debit amount",
    "debit amt", "dr amount", "dr amt", "paid out", "amount debited",
)
CREDIT_ALIASES = (
    "credit", "deposit", "deposit amount", "deposit amt", "credit amount",
    "credit amt", "cr amount", "cr amt", "paid in", "amount credited",
)
AMOUNT_ALIASES = (
    "amount", "transaction amount", "transaction amt", "txn amount", "txn amt",
)
BALANCE_ALIASES = (
    "balance", "closing balance", "running balance", "available balance",
    "balance amount", "balance amt",
)
TYPE_ALIASES = (
    "type", "dr cr", "cr dr", "debit credit", "credit debit",
    "transaction type", "txn type", "direction",
)
REFERENCE_ALIASES = (
    "reference", "ref no", "reference no", "transaction id", "txn id", "utr",
    "utr no", "cheque no", "chq no", "chq ref no", "cheque ref no",
    "reference number",
)


def _decode(data):
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not read this CSV encoding.")


def _read_delimited(data):
    text = _decode(data)
    try:
        raw = pd.read_csv(
            StringIO(text), header=None, dtype=str, keep_default_na=False,
            sep=None, engine="python",
        )
    except (pd.errors.ParserError, csv.Error):
        raw = pd.read_csv(StringIO(text), header=None, dtype=str, keep_default_na=False)
    header = tools._guess_header_row(raw)
    try:
        return pd.read_csv(
            StringIO(text), header=header, dtype=str, keep_default_na=False,
            sep=None, engine="python",
        )
    except (pd.errors.ParserError, csv.Error):
        return pd.read_csv(StringIO(text), header=header, dtype=str, keep_default_na=False)


def _read_tabular(data, suffix):
    if suffix == ".csv":
        return _read_delimited(data)
    raw = pd.read_excel(BytesIO(data), header=None, dtype=str, keep_default_na=False, engine="openpyxl")
    header = tools._guess_header_row(raw)
    return pd.read_excel(BytesIO(data), header=header, dtype=str, keep_default_na=False, engine="openpyxl")


def _date(value):
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    if re.fullmatch(r"\d{5}(?:\.0)?", text):
        serial = float(text)
        if 20000 <= serial <= 80000:
            parsed = pd.Timestamp("1899-12-30") + pd.to_timedelta(serial, unit="D")
            return parsed.date().isoformat()
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return None
    return parsed.date().isoformat()


def install():
    tools.DATE_ALIASES = DATE_ALIASES
    tools.DESCRIPTION_ALIASES = DESCRIPTION_ALIASES
    tools.DEBIT_ALIASES = DEBIT_ALIASES
    tools.CREDIT_ALIASES = CREDIT_ALIASES
    tools.AMOUNT_ALIASES = AMOUNT_ALIASES
    tools.BALANCE_ALIASES = BALANCE_ALIASES
    tools.TYPE_ALIASES = TYPE_ALIASES
    tools.REFERENCE_ALIASES = REFERENCE_ALIASES
    tools._read_tabular = _read_tabular
    tools._date = _date
