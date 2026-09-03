from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import Settings


class MongoService:
    """Owns the Mongo client and creates the indexes FinCore relies on."""

    def __init__(self, settings: Settings) -> None:
        self._client = AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5_000,
            tz_aware=True,
        )
        self.database: AsyncIOMotorDatabase = self._client[settings.mongodb_database]

    async def ping(self) -> None:
        await self.database.command("ping")

    async def ensure_indexes(self) -> None:
        await self.database.users.create_index("google_sub", unique=True, name="uq_users_google_sub")
        await self.database.users.create_index("email", unique=True, name="uq_users_email")
        await self.database.invoices.create_index(
            [("user_id", 1), ("razorpay_invoice_id", 1)], unique=True, name="uq_invoices_user_razorpay"
        )
        await self.database.payments.create_index(
            [("user_id", 1), ("razorpay_payment_id", 1)], unique=True, name="uq_payments_user_razorpay"
        )
        await self.database.settlements.create_index(
            [("user_id", 1), ("razorpay_settlement_id", 1)], unique=True, name="uq_settlements_user_razorpay"
        )
        await self.database.matches.create_index([("user_id", 1), ("invoice_id", 1)], name="matches_by_invoice")
        await self.database.exceptions.create_index([("user_id", 1), ("status", 1)], name="exceptions_by_status")

    def close(self) -> None:
        self._client.close()

