# 4. Technology stack options

Three ways to build the same system, from "runs on my laptop" to "enterprise cloud". This repository implements **Option B**, and its code also runs as **Option A** (defaults) and deploys to **Option C** (AWS mapping) without changes.

## Option A: Beginner (local only)

```
Browser ──► Flask/FastAPI (localhost:8000) ──► SQLite file
                                          └──► uploads/ folder
```

| | |
|---|---|
| Frontend | HTML, CSS, JavaScript (or the React app pointed at localhost) |
| Backend | Python Flask or FastAPI |
| Database | SQLite (`portal.db`) |
| Storage | Local folder |
| **Difficulty** | ★☆☆☆☆ |
| **Cost** | Free, no internet needed |
| **Cloud concepts shown** | Client-server, REST, authentication, RBAC, separating files from metadata |
| **Advantages** | Zero setup; easy to debug; understand every moving part first |
| **Limitations** | Not reachable from other devices; no backups; disk is a single point of failure; not "cloud" yet |

In this repo: just use the defaults (`DATABASE_URL=sqlite:///./portal.db`, `STORAGE_PROVIDER=local`). The local provider imitates object storage, including signed URLs, so moving to the cloud later is a config change.

## Option B: Recommended cloud version (free tier) ✅ implemented

```
Browser ─► Vercel CDN (React) ─► Render (FastAPI, Docker/Python) ─┬─► Supabase / Neon PostgreSQL
                                                                  └─► Supabase Storage (S3 API) / Cloudflare R2
```

| | |
|---|---|
| Frontend | React 18 + Vite, hosted on **Vercel** or **Netlify** (global CDN, HTTPS) |
| Backend | **FastAPI** on **Render** free web service (`render.yaml`) |
| Authentication | Built-in bcrypt + JWT (provider-neutral). Can be swapped for Supabase Auth / Firebase Auth / Cognito in `cloud/auth_service.py` |
| Database | **Supabase PostgreSQL** or **Neon** (free tier) |
| Cloud storage | **Supabase Storage** through its S3-compatible endpoint, or **Cloudflare R2** (S3 API, no egress fees) |
| **Difficulty** | ★★★☆☆ |
| **Cost** | ₹0 on free tiers. Limits change, so check them. Typical: DB ~0.5 GB, storage 1–10 GB, backend sleeps after ~15 min idle |
| **Cloud concepts shown** | SaaS, PaaS, DBaaS, object storage, signed URLs, CDN, env-var secrets, health checks, CI/CD, managed TLS |
| **Advantages** | Real public URL for your résumé; managed DB with backups; no credit card for most tiers; same code as local |
| **Limitations** | Cold starts on free backend; small quotas; less control than raw AWS; vendor limits |

Why FastAPI over Flask: automatic request validation (Pydantic), async file reads, and **automatic OpenAPI/Swagger docs** at `/docs`, which is great proof in screenshots and interviews.

Why S3-compatible storage: learning the S3 API means the same code works on AWS S3, Supabase, R2, MinIO, Backblaze B2, DigitalOcean Spaces and Wasabi.

## Option C: Advanced cloud version (AWS / Azure / GCP)

```
Users ─► CloudFront (CDN) ─► S3 (React build)
      └► API Gateway ─► Lambda (FastAPI via Mangum)  or  App Runner/ECS (Docker)
                          ├─► RDS PostgreSQL (Multi-AZ) + RDS Proxy
                          ├─► S3 bucket (private, SSE-KMS, versioning, lifecycle)
                          ├─► Cognito (optional user pools)
                          ├─► SQS ─► Lambda worker (virus scan, notifications)
                          └─► CloudWatch Logs/Metrics/Alarms, Secrets Manager, WAF
```

| | |
|---|---|
| Frontend | React / Next.js on S3 + CloudFront (or Amplify Hosting) |
| Backend | FastAPI on Lambda (`backend/lambda_handler.py`) behind API Gateway, or App Runner/ECS Fargate with the `Dockerfile` |
| Database | Amazon RDS / Aurora PostgreSQL (or DynamoDB if you redesign for NoSQL) |
| Storage | Amazon S3 |
| Auth | Amazon Cognito (or keep JWT with the secret in Secrets Manager) |
| Monitoring | CloudWatch logs, metrics, alarms; X-Ray tracing |
| **Difficulty** | ★★★★★ |
| **Cost** | AWS Free Tier covers small usage for 12 months or credits; RDS and NAT gateways can cost money after that, so **set a billing alarm** |
| **Cloud concepts shown** | Everything in B, plus API Gateway, FaaS, IAM roles, KMS, VPC, queues, WAF, infrastructure-as-code |
| **Advantages** | Industry-standard; fine-grained IAM; autoscaling; multi-AZ high availability |
| **Limitations** | Steep learning curve; easy to overspend; more configuration |

Azure equivalent: Static Web Apps + Front Door → API Management → Azure Functions / Container Apps → Azure Database for PostgreSQL → Blob Storage (SAS URLs) → Entra ID → Azure Monitor.
GCP equivalent: Firebase Hosting / Cloud CDN → API Gateway → Cloud Run / Cloud Functions → Cloud SQL → Cloud Storage (signed URLs) → Identity Platform → Cloud Logging and Monitoring.

## Recommendation for students

**Build Option A first (1–2 days), then deploy Option B.** It costs nothing, gives you a live URL to show, and uses the same code. Explain Option C in your report and interview as "how I would run it at scale on AWS", using `lambda_handler.py` and the `Dockerfile` as proof that the code is ready for it.
