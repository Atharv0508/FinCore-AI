"""Pure-Python reconciliation rules used before any AI-assisted analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Iterable, Literal

Classification = Literal["Paid", "Partial", "Unpaid", "Exception"]


@dataclass(frozen=True)
class MatchingConfig:
    email_date_window_days: int = 7
    amount_date_window_days: int = 30
    amount_tolerance_paise: int = 100  # INR 1.00
    fee_rate: float = 0.02
    gst_rate: float = 0.18
    small_variance_paise: int = 100  # INR 1.00


@dataclass
class ReconciliationResult:
    invoice_id: str
    payment_ids: list[str]
    settlement_ids: list[str]
    classification: Classification
    match_tier: int
    confidence: float
    evidence: list[dict[str, Any]] = field(default_factory=list)
    settlement_delta: int | None = None
    explanation: str | None = None

    def to_document(self) -> dict[str, Any]:
        return asdict(self)


def _identifier(document: dict[str, Any], preferred_key: str) -> str:
    value = document.get(preferred_key, document.get("_id", ""))
    return str(value)


def _amount(document: dict[str, Any], field_name: str = "amount") -> int:
    value = document.get(field_name, 0)
    return value if isinstance(value, int) and value >= 0 else 0


def _email(document: dict[str, Any]) -> str | None:
    value = document.get("email") or document.get("customer_email")
    return value.strip().lower() if isinstance(value, str) and value.strip() else None


def _date(document: dict[str, Any]) -> date | None:
    for key in ("captured_at", "paid_at", "issued_at", "due_at", "created_at"):
        value = document.get(key)
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
    return None


def _days_apart(first: dict[str, Any], second: dict[str, Any]) -> int | None:
    first_date, second_date = _date(first), _date(second)
    return abs((first_date - second_date).days) if first_date and second_date else None


def _eligible_payments(payments: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    # Failed and refunded payments must never make an invoice look paid.
    return [payment for payment in payments if payment.get("status") in {"captured", "authorized"}]


class DeterministicMatcher:
    def __init__(self, config: MatchingConfig | None = None) -> None:
        self.config = config or MatchingConfig()

    def reconcile(
        self,
        invoices: Iterable[dict[str, Any]],
        payments: Iterable[dict[str, Any]],
        settlements: Iterable[dict[str, Any]],
    ) -> list[ReconciliationResult]:
        invoices_list = list(invoices)
        payments_list = _eligible_payments(payments)
        settlements_by_id = {
            _identifier(item, "razorpay_settlement_id"): item for item in settlements
        }
        used_payment_ids: set[str] = set()
        results: list[ReconciliationResult] = []

        for invoice in invoices_list:
            invoice_id = _identifier(invoice, "razorpay_invoice_id")
            matches, tier, confidence, evidence = self._find_matches(invoice, payments_list, used_payment_ids)
            payment_ids = [_identifier(payment, "razorpay_payment_id") for payment in matches]
            used_payment_ids.update(payment_ids)
            matched_amount = sum(_amount(payment) for payment in matches)
            expected_amount = _amount(invoice)
            classification = self._classify(
                expected_amount,
                matched_amount,
                tier,
                ambiguous=evidence[0]["type"].startswith("ambiguous_"),
            )
            settlement_ids, settlement_delta, settlement_explanation = self._settlement_check(
                matches, payments_list, settlements_by_id
            )
            if settlement_explanation:
                evidence.append({"type": "settlement_fee_check", "message": settlement_explanation})
            results.append(
                ReconciliationResult(
                    invoice_id=invoice_id,
                    payment_ids=payment_ids,
                    settlement_ids=settlement_ids,
                    classification=classification,
                    match_tier=tier,
                    confidence=confidence,
                    evidence=evidence,
                    settlement_delta=settlement_delta,
                    explanation=settlement_explanation,
                )
            )
        return results

    def _find_matches(
        self, invoice: dict[str, Any], payments: list[dict[str, Any]], used: set[str]
    ) -> tuple[list[dict[str, Any]], int, float, list[dict[str, Any]]]:
        candidates = [p for p in payments if _identifier(p, "razorpay_payment_id") not in used]
        invoice_id = _identifier(invoice, "razorpay_invoice_id")

        exact = [payment for payment in candidates if payment.get("invoice_id") == invoice_id]
        if exact:
            return exact, 1, 1.0, [{"type": "exact_invoice_id", "invoice_id": invoice_id}]

        email = _email(invoice)
        amount = _amount(invoice)
        email_exact = [
            payment for payment in candidates
            if email and _email(payment) == email and _amount(payment) == amount
            and (_days_apart(invoice, payment) is None or _days_apart(invoice, payment) <= self.config.email_date_window_days)
        ]
        if len(email_exact) == 1:
            payment = email_exact[0]
            return [payment], 2, 0.92, [{
                "type": "email_amount_date", "email": email,
                "date_difference_days": _days_apart(invoice, payment),
            }]
        if len(email_exact) > 1:
            return [], 4, 0.0, [{"type": "ambiguous_email_amount_candidates", "count": len(email_exact)}]

        tolerant = [
            payment for payment in candidates
            if abs(_amount(payment) - amount) <= self.config.amount_tolerance_paise
            and (_days_apart(invoice, payment) is None or _days_apart(invoice, payment) <= self.config.amount_date_window_days)
        ]
        if len(tolerant) == 1:
            payment = tolerant[0]
            return [payment], 3, 0.72, [{
                "type": "amount_tolerance", "amount_delta": _amount(payment) - amount,
                "date_difference_days": _days_apart(invoice, payment),
            }]
        if len(tolerant) > 1:
            return [], 4, 0.0, [{"type": "ambiguous_amount_candidates", "count": len(tolerant)}]
        return [], 4, 0.0, [{"type": "no_deterministic_match"}]

    @staticmethod
    def _classify(expected: int, paid: int, tier: int, ambiguous: bool = False) -> Classification:
        if tier == 4 and ambiguous:
            return "Exception"
        if paid == 0:
            return "Unpaid"
        if paid < expected:
            return "Partial"
        if paid == expected:
            return "Paid"
        return "Exception"

    def _settlement_check(
        self,
        matched_payments: list[dict[str, Any]],
        all_payments: list[dict[str, Any]],
        settlements_by_id: dict[str, dict[str, Any]],
    ) -> tuple[list[str], int | None, str | None]:
        linked_ids = {
            str(payment.get("settlement_id") or payment.get("raw", {}).get("settlement_id"))
            for payment in matched_payments
            if payment.get("settlement_id") or payment.get("raw", {}).get("settlement_id")
        }
        linked_ids.intersection_update(settlements_by_id)
        if not linked_ids:
            return [], None, "No linked Razorpay settlement is available for fee validation."

        gross = sum(_amount(payment) for payment in matched_payments)
        expected_net = round(gross * (1 - self.config.fee_rate * (1 + self.config.gst_rate)))
        allocated_actual = 0.0
        for settlement_id in linked_ids:
            settlement = settlements_by_id[settlement_id]
            linked_payment_total = sum(
                _amount(payment) for payment in all_payments
                if str(payment.get("settlement_id") or payment.get("raw", {}).get("settlement_id")) == settlement_id
            )
            matching_total = sum(
                _amount(payment) for payment in matched_payments
                if str(payment.get("settlement_id") or payment.get("raw", {}).get("settlement_id")) == settlement_id
            )
            if linked_payment_total:
                allocated_actual += _amount(settlement) * matching_total / linked_payment_total
        delta = round(allocated_actual) - expected_net
        if abs(delta) <= self.config.small_variance_paise:
            explanation = (
                f"Settlement variance of {delta} paise is within INR "
                f"{self.config.small_variance_paise / 100:.2f} tolerance under the 2% fee + 18% GST model."
            )
        else:
            explanation = (
                f"Settlement differs by {delta} paise from the estimated 2% fee + 18% GST net amount; review as a fee variance."
            )
        return sorted(linked_ids), delta, explanation
