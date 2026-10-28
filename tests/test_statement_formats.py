import pytest

import statement_formats
import statement_tools
from csv_tools import detect_type

statement_formats.install()


def test_semicolon_bank_csv_with_preamble_and_common_headers():
    data = """FYNTRA SAMPLE BANK;;;;;\nAccount Number;XXXX4821;;;;\nTransaction Date;Transaction Remarks;Withdrawal Amt.;Deposit Amt.;Closing Balance;Chq./Ref.No.\n01/10/2026;UPI SWIGGY ORDER;620.00;;104380.00;UPI-1\n02/10/2026;SALARY CREDIT NEFT;;55000.00;159380.00;NEFT-1\n""".encode("utf-8")
    frame, source_type, note = statement_tools.extract_statement("statement.csv", data)
    assert source_type == "csv"
    assert len(frame) == 2
    assert frame.kind.tolist() == ["expense", "income"]
    assert frame.category.tolist() == ["Food", "Salary"]
    assert frame.reference.tolist() == ["UPI-1", "NEFT-1"]
    assert frame.balance.tolist() == [104380.0, 159380.0]
    assert "Columns detected" in note


def test_amount_and_type_columns_are_understood():
    data = """Txn Dt,Narration,Txn Amt,Dr/Cr,Available Balance,UTR No\n03/10/2026,IMPS CLIENT PAYMENT,12500.00,CR,171880.00,IMPS-22\n04/10/2026,POS AMAZON,3299.00,DR,168581.00,POS-23\n""".encode("utf-8")
    frame, _, _ = statement_tools.extract_statement("statement.csv", data)
    assert frame.kind.tolist() == ["income", "expense"]
    assert frame.amount.tolist() == [12500.0, 3299.0]
    assert frame.payment_method.tolist() == ["Bank transfer", "Card"]


def test_excel_serial_date_is_supported():
    assert statement_tools._date("45566") == "2024-10-01"


def test_backup_importer_identifies_bank_statement_csv():
    with pytest.raises(ValueError, match="looks like a bank statement"):
        detect_type(["Transaction Date", "Narration", "Debit", "Credit", "Balance"])
