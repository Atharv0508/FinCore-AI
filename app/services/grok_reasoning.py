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

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
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
    """Normalize Groq JSON mode output into FinCore's persisted exception schema."""
    try:
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("JSON response must be an object")
        # JSON mode guarantees JSON, but not every model follows every field name perfectly.
        normalized = {
            "likely_cause": data.get("likely_cause") or data.get("cause") or data.get("answer") or "Unresolved reconciliation case.",
            "recommended_action": data.get("recommended_action") or data.get("action") or "Review the source payment and invoice records.",
            "confidence": data.get("confidence", 0.5),
            "severity": data.get("severity", "medium"),
            "requires_human_review": data.get("requires_human_review", True),
            "evidence_refs": data.get("evidence_refs") or data.get("cited_exception_ids") or [],
        }
        if normalized["severity"] not in {"low", "medium", "high"}:
            normalized["severity"] = "medium"
        if not isinstance(normalized["confidence"], (int, float)):
            normalized["confidence"] = 0.5
        normalized["confidence"] = max(0, min(1, float(normalized["confidence"])))
        if not isinstance(normalized["evidence_refs"], list):
            normalized["evidence_refs"] = []
        return AIExceptionReasoning.model_validate(normalized)
    except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("Grok returned JSON that does not match FinCore's reasoning schema.") from error


class GrokReasoningService:
    def __init__(self, database, settings: Settings) -> None:
        self.database = database
        self.settings = settings

    async def answer_exception_question(self, question: str, exceptions: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")
        schema={"name":"exception_answer","strict":True,"schema":{"type":"object","properties":{"answer":{"type":"string"},"cited_exception_ids":{"type":"array","items":{"type":"string"}}},"required":["answer","cited_exception_ids"],"additionalProperties":False}}
        payload={"model":self.settings.groq_model,"temperature":0,"messages":[{"role":"system","content":"Answer only from supplied exception records. Return valid JSON only in exactly this shape: {\"answer\":\"short evidence-based answer\",\"cited_exception_ids\":[]}. Do not use Markdown."},{"role":"user","content":json.dumps({"question":question,"exceptions":exceptions},default=_json_default)}],"response_format":{"type":"json_object"}}
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response=await client.post(GROQ_CHAT_URL,headers={"Authorization":f"Bearer {self.settings.groq_api_key}","Content-Type":"application/json"},json=payload)
                if response.is_error:
                    try: detail=response.json().get("error",{}).get("message",response.text)
                    except ValueError: detail=response.text
                    raise RuntimeError(f"Grok request failed ({response.status_code}): {detail}")
            content=response.json()["choices"][0]["message"]["content"]
            parsed=json.loads(content)
            answer=parsed.get("answer") if isinstance(parsed,dict) else None
            if not isinstance(answer,str) or not answer.strip():
                # Some JSON-mode models use a differently named text field. Preserve a useful answer safely.
                answer=next((value for value in parsed.values() if isinstance(value,str) and value.strip()),None) if isinstance(parsed,dict) else None
            if not isinstance(answer,str) or not answer.strip():
                raise ValueError("response did not contain an answer string")
            citations=parsed.get("cited_exception_ids",[]) if isinstance(parsed,dict) else []
            return {"answer":answer,"cited_exception_ids":citations if isinstance(citations,list) else []}
        except RuntimeError:
            raise
        except (httpx.HTTPError,KeyError,IndexError,TypeError,ValueError) as error:
            raise RuntimeError(f"Grok returned an invalid structured answer: {error}") from error

    async def explain_tier_four(
        self,
        user_id: str,
        result: ReconciliationResult,
        invoice: dict[str, Any],
        candidate_payments: list[dict[str, Any]],
    ) -> AIExceptionReasoning:
        if result.match_tier != 4:
            raise ValueError("Grok may only be called for unresolved Tier-4 reconciliation cases.")
        if not self.settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        evidence = {
            "invoice": invoice,
            "deterministic_result": result.to_document(),
            "candidate_payments": candidate_payments[:10],
        }
        payload = {
            "model": self.settings.groq_model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(evidence, default=_json_default, separators=(",", ":"))},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.settings.groq_api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=10.0)) as client:
                response = await client.post(GROQ_CHAT_URL, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise RuntimeError("Groq rejected the reasoning request. Check GROQ_API_KEY and model access.") from error
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
