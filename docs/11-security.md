# 21. Cloud security

Security is applied in layers ("defence in depth"). No single control is trusted alone.

| Control | What it is | How this project implements it |
|---|---|---|
| **Authentication** | Prove identity | bcrypt password check → signed JWT (`cloud/auth_service.py`) |
| **Authorization** | Decide what an identity may do | `require_roles(...)` on routes + ownership checks in services |
| **RBAC** | Permissions grouped by role | `student` / `teacher` / `admin`; matrix in [03-roles-and-permissions.md](03-roles-and-permissions.md) |
| **HTTPS** | TLS between browser and server | Automatic certificates on Vercel/Render/CloudFront; API served only over HTTPS in the cloud |
| **Encryption in transit** | Data encrypted on every hop | Browser↔CDN↔API (TLS), API↔PostgreSQL (`sslmode=require` on Supabase/Neon/RDS), API↔S3 (HTTPS endpoints) |
| **Encryption at rest** | Stored data encrypted on disk | Managed PostgreSQL encrypts storage; S3 `ServerSideEncryption=AES256` or SSE-KMS (`S3_SERVER_SIDE_ENCRYPTION`); Supabase/R2 encrypt by default |
| **Password hashing** | Never store passwords | bcrypt, per-password salt, cost 12 (`BCRYPT_ROUNDS`), 72-byte limit enforced; policy: 8+ chars with letter + digit |
| **Token security** | Short-lived, verifiable, revocable | HS256 JWT with `exp` (60 min), `iss`, `jti`; revocation list checked each request; role re-read from DB |
| **Secure file uploads** | Treat every file as hostile | Generated object keys; sanitized display names; bytes never executed; files served with `Content-Disposition` + `nosniff` |
| **File-type validation** | Allow-list, not block-list | Per-assignment whitelist ⊆ portal whitelist; **magic-byte check** (`%PDF-`, `PK\x03\x04`, PNG/JPEG signatures); text types must decode as UTF-8 |
| **File-size validation** | Prevent storage/memory abuse | Server reads at most portal limit + 1 byte, then enforces the assignment limit → 413; client checks first for UX |
| **Malware scanning (concept)** | Detect infected uploads | `scan_for_malware()` hook. Production: ClamAV container, or S3 `ObjectCreated` → SQS → Lambda scanner / GuardDuty Malware Protection for S3 → quarantine prefix + mark submission |
| **Signed URLs** | Temporary permission to one object | AWS SigV4 pre-signed GET (S3) or HMAC-SHA256 URL (local); 300 s lifetime; issued only after authorization; audited (`FILE_ACCESS_GRANTED`) |
| **Storage permissions** | Least privilege on the bucket | Block public access; only the backend's key/role can read/write `assignments/*`; IAM policy in [05-cloud-storage-design.md](05-cloud-storage-design.md) |
| **Database permissions** | Least privilege in the DB | App uses a dedicated DB user with rights on its schema only (not the superuser); DB not publicly exposed where the platform allows private networking; Supabase: keep Row Level Security on for tables exposed through its public API |
| **Environment variables** | Config outside code | `backend/config.py`; `.env` in `.gitignore`; `.env.example` has placeholders only |
| **Secrets management** | Store and rotate secrets safely | Render encrypted env vars (`generateValue: true`), AWS Secrets Manager / Azure Key Vault / GCP Secret Manager in the advanced design; production refuses to start without `SECRET_KEY` |
| **CORS** | Which websites may call the API from a browser | Explicit `CORS_ORIGINS` list, no `*`; only needed methods and headers |
| **Rate limiting** | Slow down brute force and abuse | 20 login/register attempts per IP per minute → 429; production: API Gateway throttling / WAF rate rules / Redis-backed limiter |
| **Input validation** | Reject bad data early | Pydantic schemas (types, lengths, ranges, email format) + business validation in services; SQLAlchemy parameterized queries (no SQL injection); React escapes output (no XSS) |
| **Security headers** | Harden browser behaviour | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy` on every response |
| **Error handling** | Don't leak internals | Generic 500 message + request ID; stack traces only in server logs |
| **Logging** | Record what happened | Structured request logs (method, path, status, latency, user, request ID) to stdout → platform log service |
| **Audit logs** | Tamper-evident trail of sensitive actions | `audit_logs` table: logins (success/failure), uploads, replacements, grades/regrades with previous marks, file access, user and assignment changes, with IP |
| **Backup** | Recover from deletion or corruption | Managed DB daily backups + point-in-time recovery (Supabase Pro / RDS); `pg_dump` cron for free tiers; S3 versioning + lifecycle; test restores each semester |

## Common cloud-security mistakes students should avoid

1. **Committing `.env`, API keys or DB passwords to GitHub.** Bots scan public repos within minutes. If it happens: **rotate the key immediately**; deleting the commit is not enough.
2. **Public buckets** "because downloads were easier". Anyone who guesses a URL gets every student's work.
3. **Trusting the frontend**: hiding a button is not authorization. Always check the role and ownership on the server.
4. **Using the client's timestamp** for deadlines.
5. **Checking only the file extension**, or using the user's filename as the storage key (path traversal, overwrites).
6. **Storing plain-text or MD5/SHA-1 passwords.** Use bcrypt/argon2.
7. **`CORS: *` with credentials**, or turning CORS off "to make it work".
8. **Long-lived or never-expiring tokens and download links.**
9. **Returning stack traces or SQL errors** to the browser.
10. **Using the database superuser / root cloud account** in the app, and no billing alerts on AWS.
11. **Using real student data** in a class project. This repo uses fictional data only.
12. **No backups, or backups never tested.**
