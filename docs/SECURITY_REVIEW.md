# Security review notes

This is a repository review, not a penetration test.

## Checked

- Payment webhooks fail closed when the signing secret is empty, and event ids are unique.
- Provider credentials in `ApplicationConfiguration` are encrypted at rest when `FIELD_ENCRYPTION_KEY` is set.
- Staff metrics and the operations dashboard are not public.
- Assistant tools query by the caller's `family_id`.
- Telegram and WhatsApp webhooks require a configured secret.
- Production settings keep secure cookies, HSTS, and `X-Frame-Options`. Sentry does not send default PII.
- Cookie analytics stay off until an explicit choice.
- `tenant_isolation_audit` reports no unscoped tenant models, and a cross-family read returns 404 rather than 403 so family ids are not confirmed.
- Passwords are stored with Argon2id, not PBKDF2 or a weaker hash.
- Login, register, and password-reset endpoints are rate limited. A tripped limit returns 429 with `Retry-After`, never 403, so clients back off instead of treating the request as permanently forbidden.
- JSON API responses carry a strict `Content-Security-Policy` in production (`default-src 'none'`, `frame-ancestors 'none'`, PostHog the only allowed connect origin). Development and the Swagger/admin HTML pages are exempt because Vite and Django admin rely on inline scripts.
- The SPA's nginx config sets CSP, HSTS, `X-Frame-Options`, a referrer policy, and immutable caching for hashed assets with `no-store` on the HTML shell.
- Uploaded media moves to S3-compatible object storage when `AWS_*` credentials are present, so user documents are not sitting on an ephemeral container disk. A partial configuration logs an error instead of silently falling back.

## Still open

- Counsel must replace the draft terms and privacy notice before production.
- Stripe and Razorpay live keys, webhook endpoints, and tax settings are not configured here.
- Volume encryption, backup retention, and restore drills are operator tasks.
- A third party should test tenant isolation against a populated production-like database.
- The service worker caches `GET /`. Do not cache authenticated API responses in a later change without an explicit allow-list.
