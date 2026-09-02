from pydantic import BaseModel, Field


class RazorpayCredentialsRequest(BaseModel):
    key_id: str = Field(min_length=8, max_length=128)
    key_secret: str = Field(min_length=8, max_length=256)


class RazorpayConnectionStatus(BaseModel):
    connected: bool
    message: str


class SyncSummary(BaseModel):
    invoices: int = 0
    payments: int = 0
    settlements: int = 0
