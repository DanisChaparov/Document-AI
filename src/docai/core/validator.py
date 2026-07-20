"""Business-rule validation — the layer that makes accountants trust the output."""
from datetime import date, datetime
from decimal import Decimal

from docai.models.schemas import Invoice, ValidationIssue

VAT_RATE = Decimal("0.16")  # KZ НДС rate — VERIFY current rate before launch
TOLERANCE = Decimal("1")  # 1 tenge tolerance for rounding
CONFIDENCE_THRESHOLD = 0.8


def validate_bin(bin_str: str | None) -> bool:
    """Validate a Kazakhstan БИН/ИИН using the official checksum algorithm."""
    if bin_str is None or len(bin_str) != 12 or not bin_str.isdigit():
        return False
    digits = [int(c) for c in bin_str]
    w1 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    w2 = [3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2]
    s = sum(d * w for d, w in zip(digits[:11], w1)) % 11
    if s == 10:
        s = sum(d * w for d, w in zip(digits[:11], w2)) % 11
        if s == 10:
            return False
    return s == digits[11]


def validate_invoice(inv: Invoice) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    # --- БИН checks ---
    for field in ("supplier_bin", "buyer_bin"):
        value = getattr(inv, field)
        if value is not None and not validate_bin(value):
            issues.append(ValidationIssue(
                field=field,
                message=f"БИН/ИИН «{value}» не проходит проверку контрольной суммы",
                severity="error",
            ))

    # --- math checks ---
    if inv.line_items and inv.subtotal is not None:
        items_sum = sum((li.total for li in inv.line_items), Decimal(0))
        if abs(items_sum - inv.subtotal) > TOLERANCE:
            issues.append(ValidationIssue(
                field="subtotal",
                message=f"Сумма позиций ({items_sum}) не совпадает с подытогом ({inv.subtotal})",
                severity="error",
            ))

    if inv.subtotal is not None and inv.vat_amount is not None:
        expected_total = inv.subtotal + inv.vat_amount
        if abs(expected_total - inv.total) > TOLERANCE:
            issues.append(ValidationIssue(
                field="total",
                message=f"Подытог + НДС ({expected_total}) не совпадает с итогом ({inv.total})",
                severity="error",
            ))
        expected_vat = (inv.subtotal * VAT_RATE).quantize(Decimal("0.01"))
        if abs(expected_vat - inv.vat_amount) > max(TOLERANCE, inv.subtotal * Decimal("0.005")):
            issues.append(ValidationIssue(
                field="vat_amount",
                message=f"НДС ({inv.vat_amount}) отличается от ожидаемых {VAT_RATE * 100}% ({expected_vat})",
                severity="warning",
            ))

    # --- date sanity ---
    if inv.doc_date:
        try:
            d = datetime.strptime(inv.doc_date, "%Y-%m-%d").date()
            if d > date.today():
                issues.append(ValidationIssue(
                    field="doc_date", message="Дата документа в будущем", severity="warning"))
            elif (date.today() - d).days > 5 * 365:
                issues.append(ValidationIssue(
                    field="doc_date", message="Документ старше 5 лет", severity="warning"))
        except ValueError:
            issues.append(ValidationIssue(
                field="doc_date", message=f"Неверный формат даты: {inv.doc_date}", severity="error"))

    # --- low-confidence flags ---
    for field, conf in inv.confidence.items():
        if conf < CONFIDENCE_THRESHOLD:
            issues.append(ValidationIssue(
                field=field,
                message=f"Низкая уверенность распознавания ({conf:.0%}) — проверьте вручную",
                severity="warning",
            ))

    return issues
