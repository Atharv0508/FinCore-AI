"""Rule-based intent detection and scoped evidence retrieval for the AI finance-controller chat.

The chat endpoint must never hand the whole database to Grok. This module looks at the
question, decides what the user is actually asking about, and fetches only the MongoDB
records needed to answer that specific question.
"""

from __future__ import annotations

import re
from typing import Any

# Matches Razorpay-style ids (inv_, pay_, order_, set_) and human invoice numbers (INV-102, INV102).
ID_PATTERN = re.compile(
    r"\b(inv_[A-Za-z0-9]+|pay_[A-Za-z0-9]+|order_[A-Za-z0-9]+|set_[A-Za-z0-9]+|INV[-_]?\d+[A-Za-z0-9]*)\b",
    re.IGNORECASE,
)

# Order matters: more specific intents are checked before the generic ones they could
# otherwise be swallowed by (e.g. "exception" before "outstanding").
INTENT_KEYWORDS: list[tuple[str, list[str]]] = [
    ("settlement_explanation", ["settle", "settlement", "deduct", "gst", "fee"]),
    ("exception_explanation", ["exception", "not reconciled", "couldn't be reconciled",
                                "could not be reconciled", "low confidence", "low-confidence"]),
    ("unmatched_payments", ["unmatched", "doesn't match", "don't match", "no invoice",
                             "no matching invoice"]),
    ("failed_payments", ["failed payment", "failed payments"]),
    ("authorized_payments", ["still authorized", "authorized payment", "pending payment"]),
    ("partially_paid_invoices", ["partially paid", "partial payment", "partial invoice"]),
    ("unpaid_invoices", ["unpaid", "not paid", "haven't paid", "hasn't paid"]),
    ("largest_outstanding", ["largest outstanding", "biggest outstanding", "highest outstanding"]),
    ("reconciliation_rate", ["reconciliation rate", "how many reconciled", "match rate"]),
    ("outstanding_amount", ["outstanding", "how much money", "total due", "amount due"]),
]


def extract_ids(question: str) -> list[str]:
    return sorted({match.group(0) for match in ID_PATTERN.finditer(question)})


def detect_intent(question: str, ids: list[str]) -> str:
    if ids:
        return "specific_transaction"
    lowered = question.lower()
    for intent, keywords in INTENT_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return intent
    return "general_analysis"


async def gather_evidence(db, user_id: str, question: str) -> dict[str, Any]:
    """Return {"intent": ..., ...scoped records...}. Only ever queries what the intent needs."""
    ids = extract_ids(question)
    intent = detect_intent(question, ids)
    evidence: dict[str, Any] = {"intent": intent}

    if intent == "specific_transaction":
        evidence["records"] = await _records_for_ids(db, user_id, ids)
        return evidence

    if intent == "settlement_explanation":
        evidence["matches_with_settlement_data"] = await db.matches.find(
            {"user_id": user_id, "settlement_delta": {"$ne": None}}
        ).sort("settlement_delta", -1).to_list(15)
        return evidence

    if intent == "exception_explanation":
        evidence["open_exceptions"] = await db.exceptions.find(
            {"user_id": user_id, "status": "open"}
        ).sort("updated_at", -1).to_list(15)
        return evidence

    if intent == "unmatched_payments":
        matches = await db.matches.find({"user_id": user_id}).to_list(None)
        matched_ids = {pid for row in matches for pid in row.get("payment_ids", [])}
        payments = await db.payments.find({"user_id": user_id}).to_list(200)
        evidence["unmatched_payments"] = [
            p for p in payments if p.get("razorpay_payment_id") not in matched_ids
        ][:20]
        return evidence

    if intent == "failed_payments":
        evidence["failed_payments"] = await db.payments.find(
            {"user_id": user_id, "status": "failed"}
        ).to_list(20)
        return evidence

    if intent == "authorized_payments":
        evidence["authorized_payments"] = await db.payments.find(
            {"user_id": user_id, "status": "authorized"}
        ).to_list(20)
        return evidence

    if intent == "partially_paid_invoices":
        evidence["matches"] = await db.matches.find(
            {"user_id": user_id, "classification": "Partial"}
        ).to_list(20)
        return evidence

    if intent == "unpaid_invoices":
        evidence["matches"] = await db.matches.find(
            {"user_id": user_id, "classification": "Unpaid"}
        ).to_list(20)
        return evidence

    if intent == "largest_outstanding":
        invoices = await db.invoices.find({"user_id": user_id}).to_list(None)
        ranked = sorted(
            invoices,
            key=lambda i: (i.get("amount", 0) or 0) - (i.get("amount_paid", 0) or 0),
            reverse=True,
        )
        evidence["invoices_by_outstanding"] = ranked[:10]
        return evidence

    if intent == "reconciliation_rate":
        rows = await db.matches.find({"user_id": user_id}).to_list(None)
        evidence["summary"] = {
            "total": len(rows),
            "by_tier": {i: sum(r.get("match_tier") == i for r in rows) for i in range(1, 5)},
        }
        return evidence

    if intent == "outstanding_amount":
        invoices = await db.invoices.find({"user_id": user_id}).to_list(None)
        evidence["total_outstanding_paise"] = sum(
            max(0, (i.get("amount", 0) or 0) - (i.get("amount_paid", 0) or 0)) for i in invoices
        )
        evidence["open_invoice_count"] = sum(
            1 for i in invoices if (i.get("amount", 0) or 0) > (i.get("amount_paid", 0) or 0)
        )
        return evidence

    # general_analysis fallback: a compact snapshot, still not the whole database.
    rows = await db.matches.find({"user_id": user_id}).to_list(None)
    evidence["summary"] = {
        "total_matches": len(rows),
        "classification": {
            k: sum(r.get("classification") == k for r in rows)
            for k in ["Paid", "Partial", "Unpaid", "Exception"]
        },
        "open_exceptions_sample": await db.exceptions.find(
            {"user_id": user_id, "status": "open"}
        ).to_list(10),
    }
    return evidence


async def _records_for_ids(db, user_id: str, ids: list[str]) -> list[dict[str, Any]]:
    or_clauses = []
    for token in ids:
        rx = {"$regex": re.escape(token), "$options": "i"}
        or_clauses += [
            {"razorpay_invoice_id": rx}, {"invoice_number": rx}, {"invoice_id": rx},
            {"razorpay_payment_id": rx}, {"razorpay_settlement_id": rx}, {"raw.order_id": rx},
        ]
    if not or_clauses:
        return []
    out: list[dict[str, Any]] = []
    for collection in ("invoices", "payments", "settlements", "matches", "exceptions"):
        docs = await getattr(db, collection).find({"user_id": user_id, "$or": or_clauses}).to_list(10)
        out += [{"collection": collection, **d} for d in docs]
    return out