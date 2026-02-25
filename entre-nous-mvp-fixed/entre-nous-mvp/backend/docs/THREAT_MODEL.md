# Threat Model (MVP)

## Goals
- Reduce **user identifiability** and **cross-session linkability**.
- Prevent trivial deanonymization via application logs, database dumps, or UI identifiers.
- Provide abuse controls without doxxing users by default.

## Non-goals (MVP)
- Guaranteed anonymity against a state-level adversary.
- End-to-end encryption where the server cannot decrypt (requires client key management, recovery, moderation redesign).

## Main risks & mitigations
1) **Metadata leakage** (IPs, device identifiers, email/phone)
   - No required email/phone.
   - Avoid storing IP/user-agent; keep access logs disabled in deployment.
   - Use rotating pseudonyms on the client (not implemented here; recommended).

2) **Database compromise**
   - Passwords hashed with Argon2.
   - Post/reply content encrypted at rest with libsodium SecretBox.

3) **Abuse / self-harm / harassment**
   - Multi-layer moderation: sync checks + async AI scoring + human review queue.
   - User flagging + auto-hide thresholds.
   - Rate limits to reduce spam.

4) **Insider risk**
   - Strict access controls, audit logging (redacted), key management via env/KMS.
   - Separate moderation service accounts in production.

## Deployment hardening checklist
- Enforce HTTPS (TLS) and HSTS.
- Disable reverse proxy access logs or anonymize.
- Store `CONTENT_ENC_KEY_B64` in a secret manager and restrict access.
- Enable database encryption at disk level.
- Add WAF/bot protection, and optionally Tor onion front if needed.

