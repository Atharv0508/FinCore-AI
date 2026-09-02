from datetime import datetime, timezone
import unittest

from app.services.deterministic_matching import DeterministicMatcher


def when(day: int) -> datetime:
    return datetime(2026, 9, day, tzinfo=timezone.utc)


class DeterministicMatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.matcher = DeterministicMatcher()

    def test_exact_invoice_link_is_paid_at_tier_one(self) -> None:
        result = self.matcher.reconcile(
            [{"razorpay_invoice_id": "inv_1", "amount": 10_000, "issued_at": when(1)}],
            [{"razorpay_payment_id": "pay_1", "invoice_id": "inv_1", "amount": 10_000, "status": "captured"}],
            [],
        )[0]
        self.assertEqual((result.classification, result.match_tier, result.confidence), ("Paid", 1, 1.0))

    def test_email_amount_date_match_is_tier_two(self) -> None:
        result = self.matcher.reconcile(
            [{"razorpay_invoice_id": "inv_1", "amount": 2_500, "customer_email": "A@Example.com", "issued_at": when(1)}],
            [{"razorpay_payment_id": "pay_1", "amount": 2_500, "email": "a@example.com", "captured_at": when(5), "status": "captured"}],
            [],
        )[0]
        self.assertEqual((result.classification, result.match_tier), ("Paid", 2))

    def test_tolerance_match_and_partial_classification(self) -> None:
        result = self.matcher.reconcile(
            [{"razorpay_invoice_id": "inv_1", "amount": 10_000, "issued_at": when(1)}],
            [{"razorpay_payment_id": "pay_1", "amount": 9_900, "captured_at": when(2), "status": "captured"}],
            [],
        )[0]
        self.assertEqual((result.classification, result.match_tier), ("Partial", 3))

    def test_ambiguous_candidates_are_not_auto_matched(self) -> None:
        result = self.matcher.reconcile(
            [{"razorpay_invoice_id": "inv_1", "amount": 1_000, "issued_at": when(1)}],
            [
                {"razorpay_payment_id": "pay_1", "amount": 1_000, "captured_at": when(2), "status": "captured"},
                {"razorpay_payment_id": "pay_2", "amount": 1_000, "captured_at": when(3), "status": "captured"},
            ], [],
        )[0]
        self.assertEqual((result.classification, result.match_tier), ("Exception", 4))

    def test_small_settlement_variance_is_explained(self) -> None:
        result = self.matcher.reconcile(
            [{"razorpay_invoice_id": "inv_1", "amount": 10_000, "issued_at": when(1)}],
            [{"razorpay_payment_id": "pay_1", "invoice_id": "inv_1", "settlement_id": "set_1", "amount": 10_000, "status": "captured"}],
            [{"razorpay_settlement_id": "set_1", "amount": 9_764}],
        )[0]
        self.assertEqual(result.settlement_delta, 0)
        self.assertIn("within", result.explanation)


if __name__ == "__main__":
    unittest.main()
