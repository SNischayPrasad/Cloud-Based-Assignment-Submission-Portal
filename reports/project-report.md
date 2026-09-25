# Cloud-Based Student Assignment Submission & Feedback Portal
### Project Report: Cloud Computing

**Submitted by:** `<Your Name>` (`<Roll No.>`) · **Course:** Cloud Computing · **Institution:** `<College>` · **Guide:** `<Faculty Name>` · **Academic year:** 2026–27

---

## Abstract

Many educational institutions still collect coursework through email attachments, messaging apps and paper. Files get lost, submission times are disputed, feedback is scattered, and nothing controls who can see whose work. This project designs and implements a **cloud-based assignment submission and feedback portal**. Teachers create assignments with deadlines and file rules, students upload work from any device, and teachers return marks and written feedback. The system uses a three-tier cloud architecture: a React single-page application served from a CDN, a stateless FastAPI REST backend on a Platform-as-a-Service, a managed PostgreSQL database for structured metadata, and private S3-compatible object storage for files. Security combines bcrypt password hashing, JSON Web Tokens with revocation, role-based and ownership-based authorization, short-lived pre-signed download URLs, and content-level file validation. Reliability features include retries with exponential backoff, compensating transactions, idempotent uploads and server-side UTC deadline evaluation. The system is verified by 67 automated tests, including simulated cloud-service outages. It runs entirely on free-tier cloud services, and a local mode needs no cloud account.

**Keywords:** cloud computing, SaaS, PaaS, object storage, managed database, JWT, RBAC, pre-signed URL, serverless, CI/CD.

## 1. Introduction

Cloud computing delivers computing resources (servers, storage, databases, networking and software) over the internet on demand, with pay-per-use pricing and elastic capacity. Education is a natural fit because its load is bursty (heavy near deadlines, idle otherwise) and its users are spread across locations and devices. This project applies these ideas to a common academic workflow: handing in assignments and getting them back marked.

## 2. Problem statement

Design and implement a secure, scalable, cloud-hosted system that lets:
* teachers create and manage assignments with deadlines, marks and file constraints, review submissions centrally, and give marks and feedback;
* students register, view their assignments, upload and resubmit work, and view their status, marks and feedback;

while ensuring files are stored durably and privately, submission times are trustworthy, and each user can access only what their role and ownership allow.

## 3. Objectives

1. Store files in cloud object storage and metadata in a cloud database.
2. Provide authentication and role-based authorization (student, teacher, admin).
3. Implement assignment CRUD with validation.
4. Implement a secure upload workflow with deadline and resubmission policies.
5. Implement grading and feedback with validation.
6. Provide role-specific dashboards.
7. Deploy on cloud infrastructure using free tiers.
8. Verify behaviour with automated tests, including failure scenarios.

## 4. Existing system

| Method | Drawbacks |
|---|---|
| Email / messaging apps | Attachment limits, lost messages, no status tracking, no access control, no central record |
| Paper | Cost, physical loss, no backup, manual mark registers |
| Shared drive folders | Everyone can see everyone's work, overwrites, no deadlines, no feedback workflow |
| Large commercial LMS | Costly licences, complex setup; not a learning vehicle for cloud concepts |

## 5. Proposed system

A cloud-hosted portal with a clear separation of concerns: **CDN-hosted client**, **stateless API**, **managed relational database** and **private object storage**. Every submission is timestamped by the server, validated, stored under a generated key, linked to a metadata record, and accessible only through authorized, expiring URLs. Teachers see every enrolled student's status on one screen. Students see marks and feedback as soon as they are saved.

## 6. User roles

| Role | Capabilities |
|---|---|
| Student | Register, log in, join courses by code, view assignments and deadlines, upload/resubmit, view own submissions, download own files, view own marks and feedback |
| Teacher | Log in, create courses, manage roster, create/update/delete assignments, view all submissions of own courses, download/view files, grade with feedback, view statistics |
| Admin | Manage users and roles, view all courses, portal-wide statistics, audit log |

## 7. Cloud computing concepts applied

| Concept | Application |
|---|---|
| SaaS | The portal is delivered to end users through a browser |
| PaaS | Backend on Render (or App Runner / Cloud Run), frontend on Vercel/Netlify |
| IaaS | Optional: the Docker image can run on a VM |
| FaaS / serverless | Lambda handler (Mangum) behind API Gateway |
| DBaaS | Managed PostgreSQL (Supabase/Neon/RDS) |
| Object storage | S3-compatible private bucket, pre-signed URLs, SSE |
| Elasticity & scalability | Stateless API, autoscaling, connection pooling |
| Availability | Health checks, managed multi-AZ services, retries |
| CDN | Static frontend at edge locations |
| Security | IAM-style least privilege, encryption in transit/at rest, secrets in env vars |
| Monitoring & logging | Structured logs, request IDs, health metrics, audit logs |
| CI/CD | GitHub Actions + auto-deploy |

## 8. Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router 6, Axios, Vite; hosted on Vercel |
| Backend | Python 3.12, FastAPI, Pydantic 2, Uvicorn; hosted on Render (Docker/Python) |
| Database | SQLAlchemy 2.0 ORM; SQLite (local) / PostgreSQL (cloud) |
| Storage | Local provider / S3-compatible (boto3): Supabase Storage, Cloudflare R2, AWS S3, MinIO |
| Security | bcrypt, PyJWT |
| Testing | pytest, FastAPI TestClient, moto |
| DevOps | Docker, Docker Compose, GitHub Actions, Render Blueprint |

## 9. System architecture

```
Users ─► CDN (React SPA) ─► REST API (FastAPI, stateless, JWT)
                                ├─► Auth service (bcrypt, JWT, revocation)
                                ├─► Services (assignments, submissions, grading, dashboards)
                                ├─► Managed PostgreSQL (metadata)
                                ├─► Private object storage (files, signed URLs)
                                └─► Logs, health metrics, audit trail
```

The backend has four layers. **Routes** handle HTTP and schemas. **Middleware** handles authentication, RBAC, rate limiting and logging. **Services** hold business rules and ownership checks. The **cloud layer** holds interchangeable database and storage providers. Detailed diagrams, including an advanced AWS design (CloudFront, API Gateway, Lambda, RDS, S3, SQS, CloudWatch), are in `docs/07-architecture.md`.

## 10. Database design

Tables: `users`, `courses`, `enrollments`, `assignments`, `submissions`, `audit_logs`, `revoked_tokens`. Relationships: teacher 1–* course 1–* assignment 1–* submission *–1 student, and student *–* course through enrollments. Integrity is enforced by primary and foreign keys, `UNIQUE(assignment_id, student_id)` (one active submission per student) and `UNIQUE(course_id, student_id)`. Indexes support login lookup, "my submissions", teacher status filters and deadline ordering. Files are **not** stored as BLOBs; the submission row stores the object key, size, content type and SHA-256 checksum. (Full schema: `docs/04-database-design.md`.)

## 11. Cloud storage design

Objects are stored in a private bucket under `assignments/assignment_{id}/student_{id}/{UTC timestamp}_{random}.{ext}`. Keys are generated by the server, so there are no collisions, no path traversal and no guessable names. The original filename is sanitized and kept only as metadata. Uploads use server-side encryption where supported. Downloads use pre-signed URLs valid for 300 seconds, issued only after authorization. (Details: `docs/05-cloud-storage-design.md`.)

## 12. Authentication

Passwords are hashed with bcrypt (cost 12). Login returns a JWT (HS256) with subject, role, unique ID (`jti`), issue time, expiry (60 min) and issuer. Each request's token is verified for signature, expiry, issuer and revocation, and the user's current role and active status are loaded from the database. Logout revokes the token's `jti`. Login and registration are rate-limited, and failed logins are audited.

## 13. Assignment management

Teachers create assignments for courses they own. Validation enforces a future deadline (stored in UTC), `0 < max_marks ≤ 1000`, allowed file types within the portal allow-list, and a per-assignment size limit within the portal maximum. Updates re-validate changed fields and refuse to lower maximum marks below an existing grade. Deletion with existing submissions requires explicit confirmation (`force`), which also removes the stored objects.

## 14. Submission workflow

The steps are: authenticate → verify enrollment → evaluate deadline using server UTC time → apply resubmission policy and idempotency key → validate extension, size and magic bytes → upload to object storage with retries → commit metadata and audit record → on commit failure, delete the uploaded object → on resubmission, delete the previous object. Statuses are NOT_SUBMITTED (computed), SUBMITTED, LATE and GRADED. A graded submission cannot be replaced.

## 15. Deadline management

A submission is SUBMITTED if `submitted_at ≤ deadline`. Otherwise it is LATE, or rejected with HTTP 403 if the assignment disallows late work (configurable per assignment, with a portal-wide default). The timestamp always comes from the server clock, because client clocks and request contents are under the user's control. All times are stored and compared as UTC and displayed in each viewer's local timezone. The `is_late` flag is kept after grading.

## 16. Feedback and grading

Only the teacher of the course (or an admin) can grade. Marks must lie between 0 and the assignment's maximum, and feedback is limited to 5,000 characters. Grading sets the status to GRADED and records the grader and time. Regrading is allowed and audited with the previous mark. Students can read marks and feedback for their own submissions only, and no student-accessible endpoint can modify them.

## 17. API design

A RESTful JSON API with 29 endpoints across auth, courses, assignments, submissions, feedback, files, dashboards, admin and health. It uses consistent status codes (200/201/400/401/403/404/409/413/415/422/429/503) and one error format, `{detail, code}`. OpenAPI documentation is generated automatically at `/docs`. (Reference: `docs/06-api-reference.md`.)

## 18. Implementation

The backend uses FastAPI dependencies for authentication and roles, Pydantic schemas for validation, and SQLAlchemy for provider-independent data access. A `StorageService` abstraction has local and S3 implementations selected by environment variable. The local provider reproduces cloud semantics with HMAC-signed, expiring URLs. The React frontend has role-based routing, an Axios interceptor that attaches tokens and handles expired sessions, a drag-and-drop uploader with progress and retry-safe idempotency keys, and dashboards for each role. A seed script creates fictional demo data.

## 19. Testing

The suite has 67 automated tests: unit tests (hashing, JWT, sanitization, validation, deadline and timezone logic), API integration tests covering all 25 specified scenarios, fault-injection tests (storage outage with retries, transient failure recovery, database failure after upload with object cleanup, database down on read, degraded health), and S3 provider tests against mocked AWS (moto). All 67 tests pass. The manual end-to-end walkthrough (teacher creates → student uploads → teacher grades → student views feedback) was also verified in the browser. (Test case table: `docs/10-testing.md`.)

## 20. Cloud deployment

Free-tier deployment: frontend on Vercel, backend on Render (blueprint `render.yaml`, health check `/api/health`), database on Supabase PostgreSQL, files on Supabase Storage through its S3-compatible API (or Cloudflare R2). GitHub Actions runs CI, and the hosting platforms auto-deploy from the main branch. An AWS mapping (CloudFront/S3, API Gateway/Lambda or App Runner, RDS, S3, Cognito, CloudWatch, Secrets Manager), with Azure and GCP equivalents, is documented. Moving from local to cloud needs only configuration changes.

## 21. Security

Controls: authentication, RBAC with ownership checks, HTTPS, encryption in transit and at rest, bcrypt, revocable short-lived tokens, private storage with expiring signed URLs, extension/size/content validation, a malware-scan hook, an explicit CORS allow-list, rate limiting, schema validation, parameterized queries, security headers, sanitized errors, secrets in environment variables, audit logging and a backup strategy. (Details: `docs/11-security.md`.)

## 22. Scalability

The API is stateless and scales horizontally. The database handles only metadata with indexed aggregate queries, and file traffic is served by object storage. For very large scale (100,000 students near a deadline), the design moves to direct-to-bucket uploads with pre-signed PUT URLs, event-driven processing through a message queue and workers, read replicas, caching and CDN delivery. (Analysis: `docs/12-scalability-and-failures.md`.)

## 23. Results

* The complete workflow operates end to end on local and cloud configurations.
* 67 of 67 automated tests pass, including outage simulations.
* Authorization rules hold: a student cannot access teacher functions or other students' work; a teacher cannot access other teachers' courses; files cannot be fetched without a valid, unexpired signature.
* The production frontend bundle is about 87 KB (gzipped JavaScript).
* The whole system runs at zero cost on free tiers.

## 24. Advantages

Access from anywhere; central record of every submission; trustworthy timestamps; immediate feedback delivery; secure, private file handling; scalable and low-cost storage; portable across cloud providers; fully tested; easy to deploy.

## 25. Limitations

Uploads currently pass through the API (suited to files ≤ 10 MB); rate limiting is per instance; the schema is created without a migration tool; malware scanning is a hook, not a real scanner; there are no notifications or plagiarism checks; free-tier backends sleep when idle.

## 26. Future scope

Direct pre-signed uploads for large files; Alembic migrations; Redis caching and distributed rate limiting; queue-based virus scanning and email/push notifications; rubric grading and inline PDF annotation; plagiarism similarity checks; SSO with Cognito, Entra ID or Google; infrastructure-as-code with Terraform; observability with OpenTelemetry; lifecycle policies to archive old submissions; analytics on submission patterns.

## 27. Conclusion

The project shows how cloud services can turn a simple academic workflow into a secure, scalable and highly available system. Keeping structured metadata in a managed database and files in private object storage, running a stateless and token-authenticated API, and enforcing authorization on the server produces a design that works both on a laptop and in the cloud with no code changes. The automated tests, including simulated cloud failures, and the free-tier deployment show that the design works in practice.

## References

1. FastAPI documentation: https://fastapi.tiangolo.com
2. SQLAlchemy 2.0 documentation: https://docs.sqlalchemy.org
3. Amazon S3 User Guide, "Sharing objects with presigned URLs": https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html
4. Supabase Storage S3 compatibility: https://supabase.com/docs/guides/storage/s3/compatibility
5. RFC 7519, JSON Web Token (JWT)
6. OWASP File Upload Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
7. The Twelve-Factor App: https://12factor.net
8. NIST SP 800-145, The NIST Definition of Cloud Computing

*All users, courses and assignments referenced in this project are fictional.*
