"""Grok-assisted reasoning for unresolved deterministic reconciliation cases only."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import Settings
from app.models.ai import AIExceptionReasoning
from app.services.deterministic_matching import ReconciliationResult

XAI_CHAT_URL = "https://api.x.ai/v1/chat/completions"
PROMPT_VERSION = "fincore-tier4-v1"

RESPONSE_SCHEMA = {
    "name": "fincore_exception_reasoning",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "likely_cause": {"type": "string"},
            "recommended_action": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "severity": {"type": "string", "enum": ["low", "medium", "high"]},
            "requires_human_review": {"type": "boolean"},
            "evidence_refs": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
        },
        "required": ["likely_cause", "recommended_action", "confidence", "severity", "requires_human_review", "evidence_refs"],
        "additionalProperties": False,
    },
}

SYSTEM_PROMPT = """You are FinCore AI's exception analyst. Analyze only the supplied financial evidence.
Never invent transactions, IDs, dates, fees, or facts. Do not claim a payment exists when evidence is absent.
The deterministic matcher already failed to resolve this Tier-4 record; explain the most likely cause and a concrete next action.
Return only an object matching the requested JSON schema. No Markdown, prose outside JSON, or additional fields."""


def _json_default(value: Any) -> str:
    return value.isoformat() if isinstance(value, datetime) else str(value)


def parse_reasoning(content: str) -> AIExceptionReasoning:
    """Reject malformed or schema-invalid model content rather than storing it."""
    try:
        return AIExceptionReasoning.model_validate_json(content)
    except ValidationError as error:
        raise RuntimeError("Grok returned JSON that does not match FinCore's reasoning schema.") from error


class GrokReasoningService:
    def __init__(self, database, settings: Settings) -> None:
        self.database = database
        self.settings = settings

    async def answer_exception_question(self, question: str, exceptions: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.settings.xai_api_key:
            raise RuntimeError("XAI_API_KEY is not configured.")
        schema={"name":"exception_answer","strict":True,"schema":{"type":"object","properties":{"answer":{"type":"string"},"cited_exception_ids":{"type":"array","items":{"type":"string"}}},"required":["answer","cited_exception_ids"],"additionalProperties":False}}
        payload={"model":self.settings.grok_model,"temperature":0,"messages":[{"role":"system","content":"Answer only from supplied exception records. Return JSON only; say evidence is unavailable when needed."},{"role":"user","content":json.dumps({"question":question,"exceptions":exceptions},default=_json_default)}],"response_format":{"type":"json_schema","json_schema":schema}}
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response=await client.post(XAI_CHAT_URL,headers={"Authorization":f"Bearer {self.settings.xai_api_key}"},json=payload); response.raise_for_status()
            return json.loads(response.json()["choices"][0]["message"]["content"])
        except (httpx.HTTPError,KeyError,IndexError,TypeError,ValueError) as error:
            raise RuntimeError("Unable to obtain a structured Grok exception answer.") from error

    async def explain_tier_four(
        self,
        user_id: str,
        result: ReconciliationResult,
        invoice: dict[str, Any],
        candidate_payments: list[dict[str, Any]],
    ) -> AIExceptionReasoning:
        if result.match_tier != 4:
            raise ValueError("Grok may only be called for unresolved Tier-4 reconciliation cases.")
        if not self.settings.xai_api_key:
            raise RuntimeError("XAI_API_KEY is not configured.")

        evidence = {
            "invoice": invoice,
            "deterministic_result": result.to_document(),
            "candidate_payments": candidate_payments[:10],
        }
        payload = {
            "model": self.settings.grok_model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(evidence, default=_json_default, separators=(",", ":"))},
            ],
            "response_format": {"type": "json_schema", "json_schema": RESPONSE_SCHEMA},
        }
        headers = {"Authorization": f"Bearer {self.settings.xai_api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=10.0)) as client:
                response = await client.post(XAI_CHAT_URL, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise RuntimeError("Grok rejected the reasoning request. Check XAI_API_KEY and model access.") from error
        except httpx.HTTPError as error:
            raise RuntimeError("Unable to reach Grok. Check the network connection and retry.") from error

        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise RuntimeError("Grok returned an unexpected response format.") from error
        if not isinstance(content, str):
            raise RuntimeError("Grok response did not contain JSON text.")
        reasoning = parse_reasoning(content)
        await self.database.exceptions.update_one(
            {"user_id": user_id, "invoice_id": result.invoice_id, "status": "open"},
            {
                "$set": {
                    "category": "unresolved_reconciliation",
                    "severity": reasoning.severity,
                    "details": {
                        "deterministic_result": result.to_document(),
                        "candidate_payment_ids": [str(item.get("razorpay_payment_id", item.get("_id", ""))) for item in candidate_payments],
                        "prompt_version": PROMPT_VERSION,
                    },
                    "ai_reasoning": reasoning.model_dump(),
                },
                "$setOnInsert": {"created_at": datetime.utcnow(), "status": "open"},
                "$currentDate": {"updated_at": True},
            },
            upsert=True,
        )
        return reasoning
