# 1. Project overview, industry relevance and cloud concepts

## 1.1 What is a Cloud-Based Student Assignment Submission & Feedback Portal?

### A. Simple explanation

Think of the tray on a teacher's desk where students drop their homework, and the pile of marked papers the teacher hands back. This portal is that tray and that pile, moved to the internet:

* The **teacher** posts an assignment with a due date.
* The **student** opens the website on a phone or laptop, anywhere, and uploads the file.
* The file goes into a secure **online file store** (cloud object storage). The details (who, when, which assignment, on time or late) are written into an **online database**.
* The **teacher** opens the file, gives marks and writes comments.
* The **student** logs in and sees the marks and comments.

Nobody emails attachments, nothing gets lost on a pen drive, and the time of submission is recorded by the server, so nobody can argue about it.

### B. Technical explanation

The system is a **three-tier cloud application**:

| Tier | Component | Cloud service type |
|---|---|---|
| Presentation | React single-page app (static files) | Static hosting + CDN (Vercel/Netlify/CloudFront) |
| Application | FastAPI REST API, stateless, JWT-authenticated | PaaS (Render/App Runner/Cloud Run) or FaaS (Lambda) |
| Data | Relational DB for metadata + object storage for files | DBaaS (Supabase/Neon/RDS) + object storage (S3/Supabase Storage/R2) |

Uploaded files are validated and written to a **private bucket** under a server-generated key. A **metadata row** (key, size, SHA-256, server timestamp, status) is committed to the database in the same request. If that commit fails, the object is deleted. Downloads never expose the bucket: the API checks authorization and returns a **pre-signed URL that expires in minutes**.

## 1.2 What problem does it solve?

| Old way | Problem | Portal |
|---|---|---|
| Email / WhatsApp attachments | Lost files, inbox limits, no structure | One place per assignment |
| Paper | Printing cost, can be lost, no backup | Digital, backed up |
| "I submitted on time!" | Client clocks and email timestamps disputed | Server UTC timestamp, SUBMITTED/LATE recorded |
| Marks in teacher's spreadsheet | Students can't see them; no history | Marks + feedback stored and visible |
| Anyone with the link sees files | Privacy breach | RBAC + private bucket + expiring links |

## 1.3 Why is cloud computing suitable?

* **Access from anywhere.** The app runs on the internet over HTTPS, so any browser works.
* **Elastic capacity.** Load spikes near deadlines; cloud platforms add instances on demand and remove them afterwards (pay per use).
* **Object storage is effectively unlimited**, highly durable (S3 is designed for 99.999999999% durability) and cheap per GB.
* **Managed services.** The provider patches the database, runs backups and handles hardware failure.
* **Security building blocks.** TLS certificates, encryption at rest, IAM and secrets managers come ready to use.
* **Low starting cost.** Everything here runs on free tiers.

## 1.4 How can students access assignments from anywhere?

The frontend is static files served from a CDN edge close to the user, and the API is a public HTTPS endpoint. A student in a hostel, at home or on mobile data opens the same URL, logs in (JWT stored in the browser), and the dashboard calls `GET /api/dashboard/student` and `GET /api/assignments`. No VPN, no campus network and no installed software is needed.

## 1.5 How do teachers manage submissions centrally?

Every submission for an assignment is one row in `submissions`, linked to the assignment and the student. `GET /api/assignments/{id}/submissions` joins the course roster with those rows, so the teacher sees **every enrolled student**, including those who have not submitted, with status, time, file and marks, all on one screen. The teacher dashboard uses aggregate SQL for totals, pending reviews and late counts across all their courses.

## 1.6 Why store assignment files in cloud object storage?

* Files are large, unstructured blobs. Object storage is built for exactly that and is priced per GB, cheaper than database storage.
* It scales without limits and keeps the database small and fast (backups, replication and queries stay quick).
* It supports **pre-signed URLs**, so browsers can download directly from storage (and, in future, upload directly) without the file going through the API.
* It adds features such as versioning, lifecycle rules (archive old work), server-side encryption and event triggers (for example, virus scan on upload).
* The API servers stay **stateless**. On PaaS platforms the local disk is **ephemeral** (wiped on redeploy), so files saved there would be lost.

## 1.7 Why store metadata in a cloud database?

Metadata is **structured and relational**: "all LATE submissions for assignments in courses taught by teacher 2" is a SQL join with filters and indexes. The database gives transactions (the submission row and audit row commit together), constraints (one submission per student per assignment) and aggregate queries for dashboards. A managed cloud database adds automatic backups, point-in-time recovery, high availability and access from any API instance.

## 1.8 How does feedback move from teacher to student?

1. Teacher opens `/submissions/{id}`. The API checks they teach the course.
2. Teacher enters marks and feedback → `POST /api/submissions/{id}/grade`.
3. Server validates `0 ≤ marks ≤ max_marks`, sets `submission_status = GRADED`, `graded_at`, `graded_by`, writes an audit row and commits.
4. Student dashboard (`GET /api/dashboard/student`) shows it under *Recent feedback*. The student can open `GET /api/submissions/{id}/feedback`.
5. The student can **read** it but there is no student endpoint that can write it.

## 1.9 The end-to-end workflow

```
Teacher
   ↓  POST /api/assignments               (role = teacher, owns course)
Creates Assignment
   ↓  INSERT INTO assignments …
Cloud Database
   ↓  GET /api/assignments  (student sees assignments of enrolled courses)
Student Dashboard
   ↓  POST /api/assignments/{id}/submit   (multipart file + JWT)
Student Uploads Assignment
   ↓  validate → PUT object (retry)
Cloud Object Storage          assignments/assignment_007/student_012/20260925T101500Z_3f9a.pdf
   ↓  INSERT INTO submissions (storage_path, checksum, submitted_at=server UTC, status)
Submission Metadata Saved
   ↓  GET /api/assignments/{id}/submissions → GET /api/submissions/{id}/download (signed URL)
Teacher Reviews Submission
   ↓  POST /api/submissions/{id}/grade
Marks + Feedback
   ↓  UPDATE submissions SET marks, feedback, status='GRADED', graded_at …
Cloud Database
   ↓  GET /api/dashboard/student · GET /api/submissions/{id}/feedback
Student Views Feedback
```

---

# 2. Industry relevance

| Sector | Real systems with the same architecture | How this project maps |
|---|---|---|
| Learning Management Systems | Moodle Cloud, Canvas, Google Classroom, Blackboard | Courses, assignments, submissions, grading, feedback |
| Universities | Thesis and coursework portals, exam-script scanning | Deadlines, late policy, audit trail, roles |
| Schools | Homework portals used on parents' phones | Anywhere access, simple dashboards |
| Corporate training | Workday Learning, SAP SuccessFactors, Cornerstone | Employees upload evidence; managers approve/score |
| Online certification | Coursera, edX peer-graded assignments, AWS/Azure certification labs | Upload → grade → certificate eligibility |
| Employee training portals | Compliance training with document sign-off | Upload evidence, audit log for regulators |
| Bootcamps | Project submission + mentor code review | ZIP / notebook uploads, rubric feedback |
| EdTech platforms | Byju's, Unacademy, Chegg-style assignment help | Multi-tenant scale, CDN, object storage for media |

## Business benefits

| Benefit | How the design delivers it |
|---|---|
| **Centralized data** | One database of record; one bucket; no scattered inboxes |
| **Remote accessibility** | HTTPS + CDN + responsive UI |
| **Scalable storage** | Object storage grows automatically; pay per GB |
| **Automated submission tracking** | Status computed and stored automatically (SUBMITTED/LATE/GRADED, NOT_SUBMITTED) |
| **Reduced paperwork** | No printing, no manual registers, dashboards replace spreadsheets |
| **Centralized feedback** | Feedback stored with the submission; students see it immediately |
| **Secure access** | Authentication, RBAC, private files, expiring links, audit logs |
| **Backup & availability** | Managed DB backups/PITR, bucket versioning, multi-AZ services, health checks |

---

# 3. Cloud computing concepts, and where each appears

| Concept | What it means | Where it is in this project |
|---|---|---|
| **Cloud computing** | On-demand computing resources over the internet, pay-as-you-go | Whole system runs on hosted services; nothing needs a local server |
| **SaaS** | Software delivered as a service through a browser | The portal itself, used by students and teachers without installing anything |
| **PaaS** | Platform runs your code; you don't manage OS/servers | Backend on Render (`render.yaml`) / App Runner / Cloud Run; frontend on Vercel (`frontend/vercel.json`) / Netlify (`frontend/netlify.toml`) |
| **IaaS** | Rent raw VMs, networks, disks | Optional: run the `Dockerfile` on an EC2/Azure VM/GCE instance. We *choose* PaaS to avoid server management |
| **Cloud database (DBaaS)** | Provider-managed database | `DATABASE_URL=postgresql://…` (Supabase/Neon/RDS) in `cloud/database_service.py`; pooled connections with `pool_pre_ping` for cloud DBs that drop idle connections |
| **Object storage** | Flat namespace of objects in buckets, accessed via HTTP API | `cloud/storage_service.py` → `S3StorageService` (`put_object`, `get_object`, `delete_object`, presign); `LocalStorageService` imitates it offline |
| **Authentication** | Proving identity | `cloud/auth_service.py` (bcrypt, JWT), `POST /api/login` |
| **Authorization** | Deciding permissions | `backend/middleware/auth.py` (`require_roles`) + service checks (`ensure_can_view_submission`, `can_manage_course`) |
| **RBAC** | Permissions attached to roles | Roles `student`, `teacher`, `admin` in `users.role`; per-route role requirements |
| **REST API** | Resource URLs + HTTP verbs + JSON | `backend/routes/*`; OpenAPI docs at `/docs` |
| **Client-server architecture** | Thin client calls a server | React (client) ↔ FastAPI (server) over HTTPS |
| **Serverless computing** | Functions run on demand, scale to zero, pay per request | `backend/lambda_handler.py` (Mangum) runs the same API on AWS Lambda + API Gateway |
| **Scalability** | Handle more load by adding resources | Stateless JWT API → horizontal scaling; indexes + aggregate queries; files off the DB |
| **Elasticity** | Scale out *and back in* automatically | PaaS autoscaling / Lambda concurrency; free tiers scale to zero when idle |
| **Availability** | System stays usable despite failures | `/api/health` for platform health checks; managed multi-AZ DB/storage; retries |
| **Load balancing** | Spread requests over instances | Provided by Render/App Runner/ALB; app honours `X-Forwarded-For` (`backend/utils/audit.py`) and runs with `--proxy-headers` |
| **CDN** | Cache static content at edge locations | Frontend `dist/` served by Vercel/Netlify/CloudFront edges |
| **API Gateway** | Managed front door for APIs (auth, throttling, routing) | AWS design: API Gateway → Lambda; throttling complements the in-app rate limiter |
| **Environment variables** | Config outside code | `backend/config.py`, `.env.example`, `render.yaml`, `docker-compose.yml` |
| **Secrets management** | Secure storage of credentials | Secrets only in `.env` (git-ignored) / Render env / AWS Secrets Manager; `SECRET_KEY` required in production; `generateValue: true` in `render.yaml` |
| **Logging** | Record events for debugging and security | Structured stdout logs with request IDs (`backend/middleware/request_logging.py`); `audit_logs` table |
| **Monitoring** | Measure health and performance | `/api/health` → DB/storage checks + request count, 4xx/5xx, average latency; platform dashboards/CloudWatch |
| **Backup** | Copies to recover from loss | Managed DB automatic backups/PITR; S3 versioning + lifecycle; documented in `docs/11-security.md` |
| **CI/CD** | Automated test/build/deploy | `.github/workflows/ci.yml` (tests, frontend build, Docker build) + Render/Vercel auto-deploy on push to `main` |
| **Cloud deployment** | Running the system on cloud infrastructure | `docs/09-cloud-deployment.md` (free tier + AWS/Azure/GCP) |
| **Containerization** | Package app + runtime as an image | `Dockerfile` (non-root, health check), `docker-compose.yml` mini-cloud |
