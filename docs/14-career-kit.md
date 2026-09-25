# 29 & 30. Résumé, LinkedIn and interview preparation

> Use these only for work you can explain line by line. Walk through each module (see the 13-day plan) before you put it on your résumé. Replace `<…>` with your own links and numbers.

## 29. Résumé / LinkedIn proof

### A. Three résumé bullet points

* **Built and deployed a cloud-native assignment submission platform** (FastAPI, React, PostgreSQL, S3-compatible object storage) on free-tier PaaS (Render, Vercel, Supabase). Files go to a private bucket and metadata to a managed database, and moving from local to cloud needs only environment-variable changes.
* **Implemented JWT authentication with token revocation, role-based access control and ownership checks** across 29 REST endpoints. Files are served through 5-minute pre-signed URLs, and uploads are checked by extension allow-list, size limit and magic bytes, with bcrypt hashing, rate limiting and an audit log.
* **Engineered for failure and scale:** retries with exponential backoff, compensating deletes when a DB write fails after an upload, idempotency keys for safe retries, and server-side UTC deadline logic. Verified by **67 automated tests**, including simulated storage and database outages and a mocked AWS S3, run in a GitHub Actions CI pipeline.

### B. Two-line project description

**Cloud-Based Assignment Submission & Feedback Portal**: a SaaS-style platform where teachers publish assignments, students upload work to private cloud object storage, and teachers return marks and feedback. Built with FastAPI, React, PostgreSQL and S3-compatible storage, with JWT/RBAC security, signed URLs, CI/CD and free-tier cloud deployment.

### C. LinkedIn project description

> **Cloud-Based Student Assignment Submission & Feedback Portal** | Cloud Computing project
>
> I designed and built a cloud-native portal that replaces emailed and paper assignments. Teachers create assignments with deadlines and file rules, students upload from any device, and teachers grade and return written feedback.
>
> ☁️ Cloud architecture: React on a CDN (Vercel) → FastAPI on PaaS (Render, Docker-ready, Lambda-ready) → managed PostgreSQL (Supabase) + private S3-compatible object storage. Metadata and files are stored separately by design.
> 🔐 Security: bcrypt + JWT with revocation, role-based access control, per-resource ownership checks, 5-minute pre-signed download URLs, magic-byte file validation, rate limiting, audit logs, secrets in environment variables.
> 🛠️ Reliability: retries with backoff, compensating transactions, idempotent uploads, server-side UTC deadlines, health checks with metrics.
> ✅ Quality: 67 automated tests (including simulated cloud outages and mocked AWS S3) in a GitHub Actions CI pipeline.
>
> Code, architecture and docs: `https://github.com/SNischayPrasad/Cloud-Based-Assignment-Submission-Portal` · Live demo: `<Vercel link>`
> #CloudComputing #AWS #FastAPI #React #PostgreSQL #DevOps

### D. Technical skills demonstrated

| Category | Skills |
|---|---|
| Cloud computing | SaaS/PaaS/IaaS/FaaS models, object storage (S3 API, pre-signed URLs, SSE, bucket policy), managed databases (PostgreSQL), CDN, API Gateway + Lambda design, health checks, autoscaling concepts, free-tier deployment (Render, Vercel, Supabase/Neon, R2) |
| Cloud security | JWT, bcrypt, RBAC, least-privilege IAM policy, CORS, rate limiting, secrets management, encryption in transit/at rest, audit logging |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy 2.0, REST API design, error handling, retries, idempotency |
| Database | Relational modelling, PK/FK, unique constraints, composite indexes, aggregate queries, SQLite → PostgreSQL portability |
| Frontend | React 18, React Router, Axios interceptors, protected routes, file upload with progress, responsive CSS, dark mode |
| DevOps | Docker, Docker Compose (Postgres + MinIO), GitHub Actions CI, Render blueprint (IaC-style), environment-based config |
| Testing | pytest, API integration tests, fault injection with monkeypatch, moto (AWS mocking) |

### E. GitHub project description

> Cloud-based student assignment submission and feedback platform featuring role-based authentication, cloud database integration, object storage, assignment management, secure file submission, grading, and feedback workflows. FastAPI · React · PostgreSQL · S3 · JWT · Docker · CI.

---

## 30. Interview preparation: 10 questions and answers

**1. Explain your project.**
"I built a cloud-based assignment submission and feedback portal. Teachers create assignments with a deadline, maximum marks and allowed file types. Students log in from any device and upload their work, and teachers review it and return marks and written feedback. Architecturally it's three tiers. A React app is served from a CDN. A stateless FastAPI backend runs on a PaaS. For data, I split the storage in two: the files go into a private S3-compatible bucket, and the metadata goes into PostgreSQL. That's the submission record with the object key, size, checksum, server timestamp, status, marks and feedback. Security is JWT authentication plus role-based and ownership-based authorization, and downloads go through five-minute pre-signed URLs. I also handled failure cases like storage outages and duplicate requests, wrote 67 automated tests, and deployed it on free tiers: Vercel, Render and Supabase."

**2. Why did you store files in object storage instead of the database?**
"Files are large unstructured blobs, and databases are built for structured, queryable rows. If I put PDFs in the database as BLOBs, the tables and backups would bloat, it would cost more per GB, and every download would load the database. Object storage is cheap and durable, and it scales without me doing anything. It also supports pre-signed URLs, so the browser downloads straight from storage and the API never streams the bytes. The two are linked by the object key stored in the submissions table. On a PaaS the container disk is ephemeral anyway, so files saved locally would disappear on redeploy."

**3. How does authentication work, and how do you log a user out if JWTs are stateless?**
"On login I verify the password against a bcrypt hash and issue a JWT signed with a secret from an environment variable. It has the user ID, role, an expiry and a unique `jti`. Each request sends it as a Bearer token, and a FastAPI dependency checks the signature, expiry and issuer. For logout, I store the token's `jti` in a revoked-tokens table and check it on every request, so a logged-out token stops working immediately. Rows are purged after the token's natural expiry. I also re-read the user's role and active flag from the database on each request. So if an admin demotes or disables someone, it applies right away instead of when the token expires."

**4. What's the difference between authentication and authorization in your system? Give an example.**
"Authentication answers 'who are you?', which is the JWT check. Authorization answers 'what can you do?', and I do it in two layers. First, a route-level role check, like `require_teacher` on the grade endpoint. Second, a resource-level ownership check in the service layer. For example, a student calling `GET /api/submissions/42` passes authentication and the role check. But the service compares `submission.student_id` with their user ID, so if it's someone else's work they get a 403. That check covers the details, feedback and download endpoints. I have a test for exactly this. Teachers are similarly limited to courses whose `teacher_id` is theirs."

**5. Walk me through what happens when a student uploads a file.**
"The request is a multipart POST with the JWT and an idempotency key. The server checks that the user is a student and is enrolled in that course. Then it takes the time from the server clock, never the client's, and decides SUBMITTED, LATE, or rejects the upload if late work isn't allowed. It applies the resubmission policy and validates the file: extension allow-list, size limit, and magic bytes, so a renamed .exe fails. The object key is generated from the assignment ID, student ID, a timestamp and a random ID. The user's filename never goes into the key. The upload to storage is retried up to three times with exponential backoff. Then the metadata row and an audit row are committed together. If that commit fails, I delete the uploaded object, so storage and the database never disagree."

**6. How do you handle failures, like the storage service or the database going down?**
"For storage, uploads are retried with exponential backoff and jitter. If it's still failing, the API returns a 503 that tells the student their submission was not saved, and nothing is written to the database. For the database, a global handler turns any database error into a clean 503 without a stack trace. If the failure comes after the file was uploaded, a compensating action deletes the orphaned object. The health endpoint checks both dependencies and returns 503 when degraded, so the platform or a monitor can alert and route traffic. I tested all of these with fault injection: I monkeypatched the storage upload and the database commit to fail and asserted the outcome."

**7. What is idempotency and why did you need it?**
"An operation is idempotent if doing it twice has the same effect as doing it once. Mobile networks often drop the response after the server has already processed the request, and then the client retries. Without protection, a retry would create a second attempt. The frontend generates an `Idempotency-Key` for each upload attempt and reuses it on retry. The server stores it with the submission, and a repeat returns the saved result with `replayed: true` instead of uploading again. For two different first uploads that race, a unique constraint on assignment and student guarantees only one row. The loser gets a 409, and its uploaded object is cleaned up."

**8. How would your system handle 100,000 students submitting near a deadline?**
"The API is stateless because of the JWTs, so it scales horizontally behind a load balancer with autoscaling, or on Lambda. The main change I'd make is direct-to-bucket uploads. The API would only authorize the upload, record a server-side timestamp and return a pre-signed PUT URL, and the browser would upload straight to S3. That takes hundreds of gigabytes of traffic off the servers. An S3 event would put a message on a queue, and workers would scan the files and mark submissions complete at a steady rate. Because the timestamp is taken at authorization, a queue backlog can't make anyone late. On the data side: connection pooling, read replicas and Redis caching for dashboards, a CDN for the frontend, and API Gateway throttling for abusive clients."

**9. How did you secure the files and the application in general?**
"The bucket is private with public access blocked, and only the backend's credentials can reach it. Users get a pre-signed URL that expires in five minutes, and only after the authorization check. Every issued link is written to the audit log. Uploads go through an extension allow-list, a size limit, a magic-byte content check and filename sanitization, and there's a hook for malware scanning. Beyond files: bcrypt passwords, short-lived revocable JWTs, an explicit CORS allow-list, rate limiting on login and register, Pydantic input validation, parameterized SQL, security headers, and no stack traces returned to clients. There are no secrets in Git. Everything is in environment variables, and production refuses to start without a secret key. HTTPS and encryption at rest come from the cloud providers."

**10. How did you deploy it, and what's the difference between your local and cloud setup?**
"The code is identical in both. Only environment variables change, following the 12-factor approach. Locally it uses SQLite and a folder that imitates object storage, including HMAC-signed URLs. I also have a Docker Compose setup with real PostgreSQL and MinIO, which speaks the S3 API. In the cloud, the frontend is on Vercel's CDN and the backend is on Render from a `render.yaml` blueprint with a health check path. The database is Supabase PostgreSQL, and files go to Supabase Storage through its S3-compatible endpoint. GitHub Actions runs the tests, the frontend build and a Docker build on every push, and Render and Vercel auto-deploy from main. That's CI/CD. For AWS I documented the mapping: CloudFront and S3, API Gateway and Lambda, which the Mangum handler already supports, RDS, S3 with encryption, and CloudWatch."
