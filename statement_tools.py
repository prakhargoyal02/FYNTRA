"""Bank statement parsing, review helpers and safe ledger import.

Uploaded source files are processed in memory. The caller decides whether the
standardized rows are saved to the private statement workspace or imported into
the main ledger.
"""
from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import Path
import re
from statistics import mean

import pandas as pd

from database import CATEGORIES, money

STANDARD_COLUMNS = [
    "include", "date", "description", "amount", "kind", "category",
    "payment_method", "balance", "reference", "confidence", "transaction_id",
]

DATE_ALIASES = ("transaction date", "txn date", "date", "value date", "posting date")
DESCRIPTION_ALIASES = ("description", "narration", "particulars", "details", "merchant", "remarks", "transaction details")
DEBIT_ALIASES = ("debit", "withdrawal", "withdrawal amount", "debit amount", "dr amount", "paid out")
CREDIT_ALIASES = ("credit", "deposit", "deposit amount", "credit amount", "cr amount", "paid in")
AMOUNT_ALIASES = ("amount", "transaction amount", "txn amount")
BALANCE_ALIASES = ("balance", "closing balance", "running balance", "available balance")
TYPE_ALIASES = ("type", "dr cr", "debit credit", "transaction type", "direction")
REFERENCE_ALIASES = ("reference", "ref no", "reference no", "transaction id", "utr", "cheque no")


def _header(value):
    value = str(value or "").strip().casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _find_column(columns, aliases):
    normalized = {_header(col): col for col in columns}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    for norm, original in normalized.items():
        if any(alias in norm for alias in aliases):
            return original
    return None


def _number(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().replace("₹", "").replace("INR", "").replace("Rs.", "").replace("Rs", "")
    if not text or text.casefold() in {"nan", "none", "-", "--"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("() ").replace(",", "")
    text = re.sub(r"[^0-9.+-]", "", text)
    if not text or text in {"+", "-", "."}:
        return None
    try:
        result = float(text)
    except ValueError:
        return None
    return -abs(result) if negative else result


def _date(value):
    if value is None or str(value).strip()=="":
        return None
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return None
    return parsed.date().isoformat()


def infer_category(description, kind="expense"):
    if kind == "income":
        text = str(description or "").casefold()
        if any(k in text for k in ("salary", "payroll", "salary credit", "wages")):
            return "Salary"
        if any(k in text for k in ("freelance", "consulting", "invoice", "client payment")):
            return "Freelance"
        return "Other"
    text = str(description or "").casefold()
    rules = [
        (("swiggy","zomato","restaurant","cafe","coffee","dominos","mcdonald"), "Food"),
        (("grocery","grocer","bigbasket","blinkit","zepto","dmart","supermarket"), "Groceries"),
        (("amazon","flipkart","myntra","ajio","shopping","retail"), "Shopping"),
        (("uber","ola","metro","railway","irctc","bus","rapido","taxi"), "Transport"),
        (("petrol","diesel","fuel","hpcl","iocl","bharat petroleum"), "Fuel"),
        (("electricity","broadband","internet","water bill","gas bill","mobile recharge","airtel","jio","vi "), "Utilities"),
        (("netflix","spotify","youtube premium","prime video","subscription"), "Subscriptions"),
        (("pharmacy","medical","hospital","clinic","apollo","medplus"), "Healthcare"),
        (("school","college","course","udemy","coursera","tuition"), "Education"),
        (("emi","loan","credit card payment"), "EMI/debt"),
        (("rent","landlord"), "Rent"),
        (("hotel","flight","airline","booking.com","makemytrip","goibibo","travel"), "Travel"),
        (("salon","spa","barber","personal care"), "Personal care"),
        (("gift","flowers"), "Gifts"),
    ]
    for words, category in rules:
        if any(word in text for word in words):
            return category
    return "Other"


def infer_payment_method(description):
    text = str(description or "").casefold()
    if "upi" in text:
        return "UPI"
    if any(k in text for k in ("atm", "cash withdrawal", "cash deposit")):
        return "Cash"
    if any(k in text for k in ("card", "pos ", "visa", "mastercard", "rupay")):
        return "Card"
    if any(k in text for k in ("neft", "imps", "rtgs", "bank transfer", "ach", "ecs")):
        return "Bank transfer"
    return "Other"


def _kind_from_type(value):
    text = str(value or "").strip().casefold()
    if text in {"cr", "credit", "c", "income", "deposit"} or "credit" in text:
        return "income"
    if text in {"dr", "debit", "d", "expense", "withdrawal"} or "debit" in text:
        return "expense"
    return None


def _guess_header_row(raw):
    limit = min(len(raw), 25)
    for idx in range(limit):
        values = {_header(v) for v in raw.iloc[idx].tolist() if str(v).strip()}
        has_date = any(any(alias in value for alias in DATE_ALIASES) for value in values)
        has_money = any(any(alias in value for alias in DEBIT_ALIASES+CREDIT_ALIASES+AMOUNT_ALIASES) for value in values)
        if has_date and has_money:
            return idx
    return 0


def _read_tabular(data, suffix):
    if suffix == ".csv":
        decoded = None
        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
            try:
                decoded = data.decode(encoding)
                break
            except UnicodeDecodeError:
                pass
        if decoded is None:
            raise ValueError("Could not read this CSV encoding.")
        raw = pd.read_csv(StringIO(decoded), header=None, dtype=str, keep_default_na=False)
        header = _guess_header_row(raw)
        return pd.read_csv(StringIO(decoded), header=header, dtype=str, keep_default_na=False)
    raw = pd.read_excel(BytesIO(data), header=None, dtype=str, keep_default_na=False, engine="openpyxl")
    header = _guess_header_row(raw)
    return pd.read_excel(BytesIO(data), header=header, dtype=str, keep_default_na=False, engine="openpyxl")


def normalize_table(frame):
    if frame.empty:
        raise ValueError("The statement has no rows.")
    frame = frame.copy()
    frame.columns = [str(col).strip() for col in frame.columns]
    date_col = _find_column(frame.columns, DATE_ALIASES)
    desc_col = _find_column(frame.columns, DESCRIPTION_ALIASES)
    debit_col = _find_column(frame.columns, DEBIT_ALIASES)
    credit_col = _find_column(frame.columns, CREDIT_ALIASES)
    amount_col = _find_column(frame.columns, AMOUNT_ALIASES)
    balance_col = _find_column(frame.columns, BALANCE_ALIASES)
    type_col = _find_column(frame.columns, TYPE_ALIASES)
    ref_col = _find_column(frame.columns, REFERENCE_ALIASES)
    if not date_col:
        best = None
        best_score = 0
        for col in frame.columns:
            score = frame[col].head(200).map(_date).notna().mean()
            if score > best_score:
                best, best_score = col, score
        date_col = best if best_score >= .45 else None
    if not date_col or not (debit_col or credit_col or amount_col):
        raise ValueError("Could not identify the date and amount columns. Export CSV/XLSX from the bank, or upload a clear PDF/screenshot.")
    rows = []
    for raw in frame.to_dict("records"):
        on = _date(raw.get(date_col))
        if not on:
            continue
        description = str(raw.get(desc_col, "") or "").strip() if desc_col else ""
        reference = str(raw.get(ref_col, "") or "").strip() if ref_col else ""
        debit = _number(raw.get(debit_col)) if debit_col else None
        credit = _number(raw.get(credit_col)) if credit_col else None
        amount = _number(raw.get(amount_col)) if amount_col else None
        kind = _kind_from_type(raw.get(type_col)) if type_col else None
        confidence = 95
        if debit not in (None, 0):
            kind, amount = "expense", abs(debit)
        elif credit not in (None, 0):
            kind, amount = "income", abs(credit)
        elif amount not in (None, 0):
            if kind is None:
                if amount < 0:
                    kind, confidence = "expense", 80
                elif str(raw.get(amount_col, "")).strip().startswith("+"):
                    kind, confidence = "income", 80
                else:
                    kind, confidence = "expense", 55
            amount = abs(amount)
        else:
            continue
        balance = _number(raw.get(balance_col)) if balance_col else None
        category = infer_category(description, kind)
        rows.append(dict(include=True,date=on,description=description or reference or "Bank transaction",
                         amount=round(float(amount),2),kind=kind,category=category,
                         payment_method=infer_payment_method(description),balance=balance,
                         reference=reference,confidence=confidence,transaction_id=""))
    if not rows:
        raise ValueError("No transaction rows were found in the statement.")
    return pd.DataFrame(rows, columns=STANDARD_COLUMNS)


DATE_PATTERN = re.compile(r"(?<!\d)(\d{1,2}[\-/\. ](?:\d{1,2}|[A-Za-z]{3,9})[\-/\. ]\d{2,4})(?!\d)")
MONEY_PATTERN = re.compile(r"(?<!\w)(?:₹|INR|Rs\.?\s*)?[-+]?\d[\d,]*(?:\.\d{1,2})?(?!\w)", re.IGNORECASE)


def normalize_text(text, base_confidence=70):
    rows = []
    for raw_line in str(text or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        match = DATE_PATTERN.search(line)
        if not match:
            continue
        on = _date(match.group(1))
        if not on:
            continue
        remainder = (line[:match.start()] + " " + line[match.end():]).strip()
        tokens = []
        for item in MONEY_PATTERN.finditer(remainder):
            value = _number(item.group())
            if value is not None:
                tokens.append((item.start(), item.end(), item.group(), value))
        if not tokens:
            continue
        marker = remainder.casefold()
        explicit_kind = "income" if re.search(r"\b(cr|credit|deposit)\b", marker) else "expense" if re.search(r"\b(dr|debit|withdrawal)\b", marker) else None
        balance = None
        if len(tokens) >= 2:
            amount_token = tokens[-2]
            balance = tokens[-1][3]
        else:
            amount_token = tokens[-1]
        amount = amount_token[3]
        if amount == 0:
            continue
        if explicit_kind:
            kind, confidence = explicit_kind, max(base_confidence, 78)
        elif amount < 0:
            kind, confidence = "expense", max(base_confidence, 72)
        elif amount_token[2].strip().startswith("+"):
            kind, confidence = "income", max(base_confidence, 72)
        else:
            kind, confidence = "expense", min(base_confidence, 55)
        description = (remainder[:amount_token[0]] + " " + remainder[amount_token[1]:]).strip()
        description = re.sub(r"\b(?:CR|DR|credit|debit)\b", "", description, flags=re.IGNORECASE)
        description = re.sub(r"\s+", " ", description).strip(" -|:")
        rows.append(dict(include=True,date=on,description=description or "Bank transaction",
                         amount=round(abs(float(amount)),2),kind=kind,
                         category=infer_category(description,kind),payment_method=infer_payment_method(description),
                         balance=balance,reference="",confidence=int(confidence),transaction_id=""))
    if not rows:
        raise ValueError("No transaction rows could be read. Try a clearer screenshot or the bank's CSV/XLSX export.")
    return pd.DataFrame(rows, columns=STANDARD_COLUMNS)


def _ocr_lines(data):
    from rapidocr import RapidOCR
    engine = RapidOCR()
    result = engine(data)
    txts = list(result.txts or [])
    boxes = list(result.boxes or [])
    scores = list(result.scores or [])
    if not txts:
        raise ValueError("No readable text was found in this image.")
    if not boxes or len(boxes) != len(txts):
        return "\n".join(txts), int(mean(scores)*100) if scores else 65
    items = []
    heights = []
    for text, box, score in zip(txts, boxes, scores or [0.7]*len(txts)):
        xs = [float(p[0]) for p in box]
        ys = [float(p[1]) for p in box]
        items.append((sum(ys)/len(ys), min(xs), text, float(score)))
        heights.append(max(ys)-min(ys))
    tolerance = max(8.0, (sum(heights)/len(heights))*0.65) if heights else 12.0
    groups = []
    for item in sorted(items, key=lambda x:(x[0],x[1])):
        if not groups or abs(item[0]-groups[-1][0][0]) > tolerance:
            groups.append([item])
        else:
            groups[-1].append(item)
    lines = [" ".join(x[2] for x in sorted(group,key=lambda x:x[1])) for group in groups]
    confidence = int(mean(x[3] for x in items)*100) if items else 65
    return "\n".join(lines), confidence


def extract_statement(filename, data):
    if len(data) > 12*1024*1024:
        raise ValueError("Statement files are limited to 12 MB each.")
    suffix = Path(filename).suffix.casefold()
    if suffix in {".csv", ".xlsx"}:
        frame = normalize_table(_read_tabular(data, suffix))
        return frame, suffix.lstrip("."), "Columns detected from the bank export."
    if suffix == ".txt":
        text = data.decode("utf-8-sig", errors="replace")
        return normalize_text(text, 75), "text", "Rows detected from statement text."
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        text, confidence = _ocr_lines(data)
        return normalize_text(text, min(confidence, 75)), "image", "Screenshot text was read with local OCR. Review low-confidence rows before saving."
    if suffix == ".pdf":
        from pypdf import PdfReader
        try:
            reader = PdfReader(BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages[:30])
        except Exception as exc:
            raise ValueError("Could not read this PDF. If it is password protected, unlock it before uploading.") from exc
        try:
            frame = normalize_text(text, 82)
            if len(frame) >= 2:
                return frame, "pdf", "Text was extracted directly from the PDF."
        except ValueError:
            pass
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(data)
        chunks = []
        confidence = []
        for index in range(min(len(pdf), 20)):
            image = pdf[index].render(scale=1.7).to_pil()
            text_part, score = _ocr_lines(image)
            chunks.append(text_part)
            confidence.append(score)
        frame = normalize_text("\n".join(chunks), min(int(mean(confidence)) if confidence else 65, 72))
        return frame, "pdf", "The PDF was scanned with OCR. Review the extracted rows carefully."
    raise ValueError("Supported files: CSV, XLSX, PDF, TXT, PNG, JPG, JPEG and WEBP.")


def clean_rows(frame):
    if frame is None or frame.empty:
        raise ValueError("No rows to save.")
    frame = frame.copy()
    if "include" in frame:
        frame = frame.loc[frame["include"].fillna(False).astype(bool)]
    if frame.empty:
        raise ValueError("Select at least one transaction row.")
    output = []
    for index, row in frame.reset_index(drop=True).iterrows():
        on = _date(row.get("date"))
        amount = _number(row.get("amount"))
        kind = str(row.get("kind","")).strip().casefold()
        if not on or amount is None or amount <= 0 or kind not in {"income","expense"}:
            raise ValueError(f"Row {index+1}: check date, amount and direction.")
        category = str(row.get("category") or "Other").strip()
        if category not in CATEGORIES:
            category = "Other"
        balance = _number(row.get("balance"))
        output.append(dict(row_key=str(index+1),date=on,description=str(row.get("description") or "Bank transaction")[:500],
                           amount=round(float(amount),2),kind=kind,category=category,
                           payment_method=str(row.get("payment_method") or "Other"),balance=balance,
                           reference=str(row.get("reference") or "")[:500],confidence=int(float(row.get("confidence") or 50)),
                           transaction_id=str(row.get("transaction_id") or "")))
    return output


def rows_frame(rows):
    frame = pd.DataFrame(rows or [])
    if frame.empty:
        return pd.DataFrame(columns=STANDARD_COLUMNS)
    frame["include"] = True
    for column in STANDARD_COLUMNS:
        if column not in frame:
            frame[column] = ""
    return frame[STANDARD_COLUMNS]


def summary(rows):
    frame = rows_frame(rows)
    if frame.empty:
        return dict(count=0,income=0.0,expenses=0.0,net=0.0,start=None,end=None,opening_balance=None,closing_balance=None)
    frame["amount"] = pd.to_numeric(frame.amount,errors="coerce").fillna(0.0)
    income = float(frame.loc[frame.kind.eq("income"),"amount"].sum())
    expenses = float(frame.loc[frame.kind.eq("expense"),"amount"].sum())
    balances = pd.to_numeric(frame.balance,errors="coerce").dropna()
    dates = pd.to_datetime(frame.date,errors="coerce").dropna()
    return dict(count=len(frame),income=income,expenses=expenses,net=income-expenses,
                start=None if dates.empty else dates.min().date().isoformat(),
                end=None if dates.empty else dates.max().date().isoformat(),
                opening_balance=None if balances.empty else float(balances.iloc[0]),
                closing_balance=None if balances.empty else float(balances.iloc[-1]))


def import_rows(store, statement_id, statement_name, account_id, rows):
    updated = [dict(row) for row in rows]
    imported = 0
    with store.connect() as con, con:
        for index, row in enumerate(updated):
            if row.get("transaction_id"):
                continue
            row_key = str(row.get("row_key") or index+1)
            source_key = f"statement:{statement_id}:{row_key}"
            existing = con.execute("SELECT id FROM transactions WHERE source_key=?",(source_key,)).fetchone()
            if existing:
                row["transaction_id"] = existing[0]
                continue
            description = str(row.get("description") or "Bank transaction")
            tx_id = store._put(con,"transactions",dict(
                date=str(row["date"]),time="12:00",amount_paise=money(row["amount"]),kind=row["kind"],
                category=row.get("category") or "Other",account_id=account_id,merchant=description,
                payment_method=row.get("payment_method") or "Other",
                notes=f"Imported from bank statement: {statement_name}",tags="statement-import",
                source_key=source_key))
            row["transaction_id"] = tx_id
            imported += 1
        store._validate_graph(con)
    if imported:
        store.revision += 1
    return updated, imported
