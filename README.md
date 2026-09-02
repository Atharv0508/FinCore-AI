# FinCore AI

Finance reconciliation platform. This repository currently implements **Phases 1–2**: the FastAPI/MongoDB foundation and Google OAuth session authentication.

## Local setup

1. Create a virtual environment: `python -m venv .venv`
2. Activate it in PowerShell: `.\.venv\Scripts\Activate.ps1`
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`, then enter the Atlas URI.
5. Run: `uvicorn app.main:app --reload`
6. Visit `http://127.0.0.1:8000/docs` and call `GET /health/database`.

The database and collections are created by MongoDB when data is first inserted. On application start, FinCore creates indexes required for user and Razorpay-resource lookups.

## Google OAuth (Phase 2)

Create a **Web application** OAuth client in [Google Cloud Console](https://console.cloud.google.com/apis/credentials). Add `http://localhost:5173` to its Authorized JavaScript origins. Put its client ID in both the root `.env` as `GOOGLE_CLIENT_ID` and `frontend/.env` as `VITE_GOOGLE_CLIENT_ID`.

Generate a random `JWT_SECRET` and put it in the root `.env`. Start the API with `uvicorn app.main:app --reload`. In a second terminal, run `cd frontend`, `npm install`, then `npm run dev`; open the shown localhost URL and sign in.

## Razorpay sync (Phase 3)

Add a `FERNET_KEY` to the root `.env`; generate it with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. After signing in, call `POST /razorpay/credentials` with test-mode `key_id` and `key_secret`, then call `POST /razorpay/sync`. The key secret is Fernet-encrypted before MongoDB storage and is never returned by the API. Sync results are paginated and upserted into the `invoices`, `payments`, and `settlements` collections.

## Deterministic matching (Phase 4)

`app/services/deterministic_matching.py` has no API, database, or AI dependency. It matches captured/authorized payments in priority order: exact Razorpay invoice ID, then unique email + exact amount + date proximity, then a unique INR 1 amount-tolerance candidate. It never auto-selects an ambiguous candidate. The engine classifies results as Paid, Partial, Unpaid, or Exception and validates linked settlements against the 2% fee + 18% GST estimate. Run `python -m unittest discover -s tests -v` to test it.

## Grok reasoning (Phase 5)

Set `XAI_API_KEY` in the root `.env` and optionally choose `GROK_MODEL` (default: `grok-4.6`). `GrokReasoningService` is deliberately callable only for Tier-4 results. It submits a strict JSON-schema response request, validates the returned JSON with Pydantic, and persists the structured reasoning in `exceptions`. No AI call occurs for Tier 1–3 matches.
