# Deal Archive

Forward your flyers, get instant comps. A broker's personal, searchable
sale/lease comp database built from flyers they already receive.

## Stack

- **Backend**: FastAPI + SQLAlchemy + Alembic + Postgres, `anthropic` for
  vision-based flyer extraction. Lives in `dealarchive/`.
- **Frontend**: Next.js (App Router) + Tailwind. Lives in `web/`.

## Local setup

### 1. Database

```bash
docker compose up -d
```

(No Docker installed on this machine at scaffold time — install Docker
Desktop, or point `DATABASE_URL` at any local/hosted Postgres 16 instance.)

### 2. Backend

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env   # fill in ANTHROPIC_API_KEY at minimum
alembic upgrade head
uvicorn dealarchive.api:app --reload
```

### 3. Frontend

```bash
cd web
npm install
cp .env.local.example .env.local
npm run dev
```

Visit http://localhost:3000.

## How ingestion works

- **Manual upload**: `POST /upload` (authenticated) accepts a PDF/image and
  runs it through the same extraction pipeline as email.
- **Email forwarding**: each broker gets a unique forwarding address
  (`<slug>@deals.dealarchive.app`, shown in Settings). Wiring this up for
  real requires an inbound-email provider (SendGrid Inbound Parse, Postmark,
  Mailgun Routes, etc.) configured to POST to `POST /ingest/email` with the
  recipient, sender, and attachment — that endpoint is built and ready, but
  actually receiving mail at `deals.dealarchive.app` needs DNS (MX records)
  and an account with one of those providers, which wasn't set up here.
  If the recipient's local-part doesn't match any user's forwarding slug,
  the endpoint returns 404 — configure the email provider to auto-reply
  "sign up first" on that response.

## Data model

`Flyer` stores the raw file + extraction status. Every `SaleComp` and
`LeaseComp` row points back to the `Flyer` it was parsed from, so the
original document is always available next to the structured data. Sale and
lease are separate tables (different fields: cap rate vs. term/NNN) sharing
one ingestion pipeline, per the product brief.

## Not done yet

- Real inbound-email wiring (see above) — needs a provider account + DNS.
- Auth is plain email/password + JWT (no Clerk/OAuth) — swap later if needed.
- File storage is local disk (`storage/`) — swap `dealarchive/storage.py`
  for S3 when deploying.
- Everything explicitly out of scope for v1 per the brief: market-wide
  charts, alerts/watchlists, comp-set PDF export, team vaults.

## Trademark / domain

The brief flagged "Deal Archive" as checked-but-unconfirmed — do an actual
USPTO trademark search and confirm domain availability before using this
name publicly.
