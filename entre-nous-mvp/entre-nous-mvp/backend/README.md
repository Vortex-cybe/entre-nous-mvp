# Entre Nous — MVP Backend (FastAPI)

## What this is
A security-first MVP backend for **Entre Nous** (anonymous social network). It implements:

- **Real-ish anonymity by design**: no public usernames, no required email/phone, minimal logging.
- **Strong technical security baseline**: TLS-ready, password hashing (Argon2), JWT auth, rate-limits, security headers.
- **RGPD/GDPR primitives**: data export + account deletion endpoints, data minimization defaults.
- **Encrypted content at rest**: posts/replies stored as authenticated ciphertext (libsodium SecretBox).
- **Moderation in layers**: (1) immediate guardrails, (2) async "AI moderation" stub, (3) human review queue.
- **Kindness ranking**: users gain trust score via positive feedback and low flags; content ranking boosts high-trust authors.

> Note: “Real anonymity” is a *threat-model question*, not a marketing checkbox. This MVP **reduces linkability** but does not guarantee anonymity against a nation‑state. See `docs/THREAT_MODEL.md`.

## Quick start (Docker)
```bash
cd backend
cp .env.example .env
docker compose up --build
```
API: `http://localhost:8000`  
Docs: `http://localhost:8000/docs`

## Quick start (local)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e .
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Key endpoints
- `POST /auth/register`  (password-based, no email required)
- `POST /auth/login (email + password)`
- `GET /feed`
- `POST /posts`
- `POST /posts/{post_id}/reply`
- `POST /moderation/flag`
- `GET /moderation/queue` (human review; admin token)
- `POST /moderation/queue/{item_id}/decision`
- `GET /me/export`
- `DELETE /me`

## Admin
Set `ADMIN_REVIEW_TOKEN` in `.env` to access moderation queue endpoints.

## Security notes
- Content is encrypted **server-side** with a key in `CONTENT_ENC_KEY_B64` (32 bytes base64). Rotate with care.
- No raw IPs are persisted (only ephemeral in memory). If you deploy behind a proxy, disable proxy logs too.
- Rate limiting uses Redis. In Docker it’s provided.


## IP ban (privacy-friendly)
- Middleware blocks requests if the client IP prefix is banned (IPv4 /24 or IPv6 rough /64).
- Admin endpoint: `POST /moderation/ban/ip?ip=1.2.3.4&reason=spam` with header `X-Admin-Token`.

This stores **encrypted IP** + an HMAC lookup token in `ip_bans` (no clear IP in DB).


## Admin dashboard (API + UI)
- Admin API: `GET /admin/overview` with header `X-Admin-Token: ADMIN_UI_TOKEN`
- Returns: p50/p95 latency (rolling last 500), status counts, moderation pending, recent flags, bans.

## Private messages (DM)
- `POST /dm/start_from_post` (open a conversation with the author of a post)
- `GET /dm/list`
- `GET /dm/{conversation_id}/messages`
- `POST /dm/{conversation_id}/send`

DM content is encrypted at rest (same SecretBox scheme as posts).

