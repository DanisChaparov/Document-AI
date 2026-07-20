from decimal import Decimal

from docai.core.validator import validate_bin, validate_invoice
from docai.models.schemas import Invoice, LineItem


def make_invoice(**kwargs) -> Invoice:
    base = dict(
        doc_type="счёт-фактура",
        doc_number="123",
        doc_date="2026-01-15",
        supplier_name="ТОО Ромашка",
        line_items=[LineItem(name="Услуга", total=Decimal("1000"))],
        subtotal=Decimal("1000"),
        vat_amount=Decimal("160"),
        total=Decimal("1160"),
    )
    base.update(kwargs)
    return Invoice(**base)


class TestValidateBin:
    def test_rejects_wrong_length(self):
        assert not validate_bin("12345")
        assert not validate_bin(None)
        assert not validate_bin("1234567890123")

    def test_rejects_non_digits(self):
        assert not validate_bin("12345678901a")

    def test_accepts_valid_checksum(self):
        # checksum-valid test БИН (verified against the algorithm)
        assert validate_bin("940840000211")

    def test_rejects_invalid_checksum(self):
        assert not validate_bin("940840000212")


class TestValidateInvoice:
    def test_clean_invoice_has_no_issues(self):
        assert validate_invoice(make_invoice()) == []

    def test_flags_line_item_mismatch(self):
        inv = make_invoice(subtotal=Decimal("9999"), vat_amount=None, total=Decimal("9999"))
        issues = validate_invoice(inv)
        assert any(i.field == "subtotal" and i.severity == "error" for i in issues)

    def test_flags_total_mismatch(self):
        inv = make_invoice(total=Decimal("5000"))
        issues = validate_invoice(inv)
        assert any(i.field == "total" for i in issues)

    def test_flags_future_date(self):
        inv = make_invoice(doc_date="2099-01-01")
        issues = validate_invoice(inv)
        assert any(i.field == "doc_date" for i in issues)

    def test_flags_bad_date_format(self):
        inv = make_invoice(doc_date="15.01.2026")
        issues = validate_invoice(inv)
        assert any(i.field == "doc_date" and i.severity == "error" for i in issues)

    def test_flags_low_confidence(self):
        inv = make_invoice(confidence={"total": 0.5})
        issues = validate_invoice(inv)
        assert any("уверенность" in i.message for i in issues)

    def test_flags_invalid_bin(self):
        inv = make_invoice(supplier_bin="123456789012")
        issues = validate_invoice(inv)
        assert any(i.field == "supplier_bin" for i in issues)
