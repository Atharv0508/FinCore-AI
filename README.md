# FinCore AI

> **Finance reconciliation, reimagined.**
>
> FinCore AI connects Razorpay data, reconciles invoices against payments and settlements, and uses AI only when deterministic evidence is not enough.

**Live application:** [fin-core-ai-m5g8.vercel.app](https://fin-core-ai-m5g8.vercel.app/)

**Backend API:** [fincore-ai.onrender.com](https://fincore-ai.onrender.com/)

## Overview

Finance teams often reconcile payment data by moving between dashboards, exports, and spreadsheets. FinCore AI brings that workflow into one place:

- Sign in securely with Google OAuth.
- Connect Razorpay using test-mode API credentials.
- Sync invoices, payments, and settlements into a MongoDB-backed workspace.
- Reconcile records with transparent, deterministic matching rules.
- Escalate genuinely ambiguous cases to an AI finance analyst.
- Monitor match rate, outstanding amounts, settlement differences, risk signals, and exceptions from one dashboard.

The product follows a simple principle: **use strong evidence first, and use AI only where the evidence runs out.**

## Key features

### Razorpay data connection

Users can securely connect Razorpay test-mode credentials and sync:

- Invoices
- Payments
- Settlements

Credentials are encrypted with Fernet before storage. The secret is used server-side for synchronization and is never returned by the API.

### Deterministic reconciliation

Every invoice is matched against eligible captured or authorized payments in a predictable priority order:

1. Exact Razorpay invoice ID
2. Unique customer email + exact amount + date proximity
3. Unique amount match within an INR 1 tolerance + date proximity
4. Exception when no safe or unique match exists

The matcher never auto-selects an ambiguous candidate. Each result includes a match tier, confidence score, evidence, classification, and linked settlement information.

Results are classified as **Paid**, **Partial**, **Unpaid**, or **Exception**.

### Settlement validation

For linked payments, FinCore estimates the expected settlement amount using a 2% fee and 18% GST model. It compares that estimate with the actual settlement and flags material variance for review.

### AI exception analysis

Tier-4 records are sent to Groq only when deterministic matching cannot safely resolve them. The AI receives the invoice, deterministic result, and a limited set of candidate payments as structured evidence. It returns:

- Likely cause
- Recommended action
- Confidence
- Severity
- Whether human review is required
- Evidence references

The response is constrained to JSON, validated with Pydantic, and stored with the exception. FinCore AI is designed to explain uncertainty, not hide it or invent missing financial facts.

### Finance assistant

The dashboard includes an evidence-grounded chat assistant for questions about exceptions and reconciliation results. It searches the user's own invoices, payments, settlements, matches, and exceptions before asking the model for an answer.

### Reconciliation dashboard

The dashboard provides:

- Match rate and auto-reconciliation metrics
- Paid, partial, unpaid, and exception breakdowns
- Outstanding, collected, and settled amounts
- Payment and settlement differences
- Recent invoices, payments, and settlements
- Open exceptions with severity indicators
- Search across IDs, customer details, emails, UTRs, and date ranges
- Transaction detail views with optional raw source data

## How the AI workflow works

```text
Razorpay invoices + payments + settlements
						  |
						  v
		  Deterministic matching engine
			 /         |          \
		 Tier 1     Tier 2/3     Tier 4
		 Exact      Evidence     Ambiguous or
		 ID         match        unresolved
			 \         |          /
			  +-------+----------+
						 |
						 v
		  Reconciliation + dashboard
						 |
						 v
			 Groq explains Tier-4 only
```

The AI service is intentionally separated from the core matcher. This makes the reconciliation rules testable without an API key and keeps model output advisory rather than authoritative.

## Tech stack

### Frontend

- React 18
- Vite
- Tailwind CSS
- Recharts for dashboard visualizations
- `@react-oauth/google` for Google sign-in

### Backend

- Python 3
- FastAPI
- Uvicorn for local development
- Gunicorn for production process management
- Pydantic and Pydantic Settings
- Motor for asynchronous MongoDB access
- PyJWT for session tokens
- `google-auth` for Google credential verification
- Cryptography/Fernet for credential encryption
- HTTPX for Razorpay and Groq API requests

### Data and services

- MongoDB Atlas for application data
- Razorpay API for payment data
- Google OAuth for authentication
- Groq API for structured AI reasoning
- Vercel for the frontend deployment
- Render for the backend deployment

## Project structure

```text
.
├── app/
│   ├── core/              # Settings and security
│   ├── models/            # Pydantic request and response models
│   ├── routers/           # Auth, health, Razorpay, and reconciliation APIs
│   └── services/          # MongoDB, Razorpay, matching, crypto, and AI logic
├── frontend/
│   └── src/
│       ├── components/    # Shared UI components
│       ├── lib/           # API client and formatting helpers
│       └── pages/         # Landing, connection, and dashboard views
├── tests/                 # Deterministic matching and AI parsing tests
├── requirements.txt       # Python dependencies
└── seed_razorpay.py       # Optional Razorpay seed/demo helper
```

## Run locally

### 1. Configure the backend

Create a virtual environment and install the Python dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file in the repository root:

```env
APP_NAME=FinCore AI API
ENVIRONMENT=development
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>/<database>
MONGODB_DATABASE=fincore
GOOGLE_CLIENT_ID=<google-web-client-id>
JWT_SECRET=<long-random-secret>
FRONTEND_ORIGIN=http://localhost:5173
COOKIE_SECURE=false
FERNET_KEY=<fernet-key>
GROQ_API_KEY=<optional-groq-api-key>
GROQ_MODEL=openai/gpt-oss-20b
```

Generate a Fernet key with:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

For Google OAuth, create a Web application client in [Google Cloud Console](https://console.cloud.google.com/apis/credentials) and add `http://localhost:5173` to its authorized JavaScript origins.

Start the API:

```powershell
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

### 2. Configure and run the frontend

In a second terminal:

```powershell
cd frontend
npm install
```

Create `frontend/.env`:

```env
VITE_GOOGLE_CLIENT_ID=<same-google-web-client-id>
VITE_API_URL=http://127.0.0.1:8000
```

Run the frontend:

```powershell
npm run dev
```

Open the Vite URL, sign in with Google, connect Razorpay test credentials, sync the data, and run reconciliation from the dashboard.

## Useful API routes

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check API health |
| `GET` | `/health/database` | Check MongoDB connectivity |
| `POST` | `/auth/google` | Create a session from a Google credential |
| `POST` | `/razorpay/credentials` | Encrypt and save Razorpay credentials |
| `POST` | `/razorpay/sync` | Import invoices, payments, and settlements |
| `POST` | `/reconcile/{user_id}` | Run deterministic reconciliation and AI escalation |
| `GET` | `/stats/{user_id}` | Load dashboard metrics and recent records |
| `GET` | `/search/{user_id}` | Search financial records and date ranges |
| `GET` | `/transactions/{user_id}` | List reconciliation results |
| `POST` | `/chat/{user_id}` | Ask an evidence-grounded finance question |

## Testing

Run the test suite from the repository root:

```powershell
python -m unittest discover -s tests -v
```

The deterministic matcher tests cover exact invoice links, email and amount matching, tolerance matching, ambiguous candidates, and settlement variance explanations. AI response parsing is tested independently so the core reconciliation engine does not depend on a live model request.

## Security notes

- Use Razorpay **test-mode** credentials during development and demos.
- Keep `.env`, OAuth secrets, JWT secrets, Fernet keys, and Groq keys out of version control.
- Credentials are encrypted before being persisted in MongoDB.
- User-scoped routes verify ownership before returning financial records.
- AI responses are constrained, schema-validated, and grounded in supplied evidence.
