import asyncio
import json
from datetime import datetime, timezone
from typing import Any

import httpx

from app.services.crypto import CredentialCipher

RAZORPAY_API_BASE = "https://api.razorpay.com/v1"
PAGE_SIZE = 100


def from_unix(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    return None


class RazorpayService:
    def __init__(self, database, cipher: CredentialCipher) -> None:
        self.database = database
        self.cipher = cipher

    async def save_credentials(self, user_id: str, key_id: str, key_secret: str) -> None:
        encrypted = self.cipher.encrypt(json.dumps({"key_id": key_id, "key_secret": key_secret}))
        now = datetime.now(timezone.utc)
        result = await self.database.users.update_one(
            {"google_sub": user_id},
            {"$set": {"razorpay_credentials_encrypted": encrypted, "credential_updated_at": now, "updated_at": now}},
        )
        if result.matched_count != 1:
            raise LookupError("User not found.")

    async def sync(self, user_id: str) -> dict[str, int]:
        user = await self.database.users.find_one({"google_sub": user_id})
        if not user or not user.get("razorpay_credentials_encrypted"):
            raise LookupError("Connect Razorpay before starting a sync.")

        try:
            credentials = json.loads(self.cipher.decrypt(user["razorpay_credentials_encrypted"]))
            key_id, key_secret = credentials["key_id"], credentials["key_secret"]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise RuntimeError("Stored Razorpay credentials are invalid. Reconnect with active test-mode keys.") from error
        if not isinstance(key_id, str) or not key_id or not isinstance(key_secret, str) or not key_secret:
            raise RuntimeError("Stored Razorpay credentials are invalid. Reconnect with active test-mode keys.")
        async with httpx.AsyncClient(
            base_url=RAZORPAY_API_BASE,
            auth=(key_id, key_secret),
            timeout=httpx.Timeout(30.0, connect=10.0),
        ) as client:
            invoices = await self._fetch_all(client, "/invoices")
            payments = await self._fetch_all(client, "/payments")
            settlements = await self._fetch_all(client, "/settlements")

        await self._upsert_invoices(user_id, invoices)
        await self._upsert_payments(user_id, payments)
        await self._upsert_settlements(user_id, settlements)
        return {"invoices": len(invoices), "payments": len(payments), "settlements": len(settlements)}

    async def _fetch_all(self, client: httpx.AsyncClient, path: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        skip = 0
        while True:
            try:
                response = await client.get(path, params={"count": PAGE_SIZE, "skip": skip})
                response.raise_for_status()
            except httpx.HTTPStatusError as error:
                message = "Razorpay rejected the request. Verify that you used active test-mode API keys."
                raise RuntimeError(message) from error
            except httpx.HTTPError as error:
                raise RuntimeError("Unable to reach Razorpay. Check your internet connection and retry.") from error

            try:
                payload = response.json()
            except ValueError as error:
                raise RuntimeError("Razorpay returned an unexpected response format.") from error
            if not isinstance(payload, dict):
                raise RuntimeError("Razorpay returned an unexpected response format.")
            page = payload.get("items")
            if not isinstance(page, list):
                raise RuntimeError("Razorpay returned an unexpected response format.")
            records.extend(item for item in page if isinstance(item, dict))
            if len(page) < PAGE_SIZE:
                return records
            skip += len(page)
            await asyncio.sleep(0)

    async def _upsert_invoices(self, user_id: str, records: list[dict[str, Any]]) -> None:
        now = datetime.now(timezone.utc)
        for raw in records:
            razorpay_id = raw.get("id")
            if not isinstance(razorpay_id, str):
                continue
            customer = raw.get("customer_details") or {}
            document = {
                "user_id": user_id, "razorpay_invoice_id": razorpay_id,
                "invoice_number": raw.get("invoice_number"), "status": raw.get("status"),
                "customer_email": customer.get("email") or raw.get("customer_email"),
                "customer_name": customer.get("name") or raw.get("customer_name"),
                "currency": raw.get("currency", "INR"), "amount": raw.get("amount", 0),
                "amount_paid": raw.get("amount_paid", 0), "issued_at": from_unix(raw.get("issued_at") or raw.get("date")),
                "due_at": from_unix(raw.get("expire_by")), "paid_at": from_unix(raw.get("paid_at")),
                "raw": raw, "synced_at": now, "updated_at": now,
            }
            await self.database.invoices.update_one(
                {"user_id": user_id, "razorpay_invoice_id": razorpay_id},
                {"$set": document, "$setOnInsert": {"created_at": now}}, upsert=True,
            )

    async def _upsert_payments(self, user_id: str, records: list[dict[str, Any]]) -> None:
        now = datetime.now(timezone.utc)
        for raw in records:
            razorpay_id = raw.get("id")
            if not isinstance(razorpay_id, str):
                continue
            document = {
                "user_id": user_id, "razorpay_payment_id": razorpay_id, "invoice_id": raw.get("invoice_id"),
                "order_id": raw.get("order_id"), "settlement_id": raw.get("settlement_id"), "email": raw.get("email"), "status": raw.get("status"),
                "method": raw.get("method"), "currency": raw.get("currency", "INR"), "amount": raw.get("amount", 0),
                "fee": raw.get("fee"), "tax": raw.get("tax"), "captured_at": from_unix(raw.get("created_at")),
                "raw": raw, "synced_at": now, "updated_at": now,
            }
            await self.database.payments.update_one(
                {"user_id": user_id, "razorpay_payment_id": razorpay_id},
                {"$set": document, "$setOnInsert": {"created_at": now}}, upsert=True,
            )

    async def _upsert_settlements(self, user_id: str, records: list[dict[str, Any]]) -> None:
        now = datetime.now(timezone.utc)
        for raw in records:
            razorpay_id = raw.get("id")
            if not isinstance(razorpay_id, str):
                continue
            document = {
                "user_id": user_id, "razorpay_settlement_id": razorpay_id, "status": raw.get("status"),
                "currency": raw.get("currency", "INR"), "amount": raw.get("amount", 0),
                "fees": raw.get("fees", 0), "tax": raw.get("tax", 0), "utr": raw.get("utr"),
                "settled_at": from_unix(raw.get("settled_at") or raw.get("created_at")),
                "raw": raw, "synced_at": now, "updated_at": now,
            }
            await self.database.settlements.update_one(
                {"user_id": user_id, "razorpay_settlement_id": razorpay_id},
                {"$set": document, "$setOnInsert": {"created_at": now}}, upsert=True,
            )
