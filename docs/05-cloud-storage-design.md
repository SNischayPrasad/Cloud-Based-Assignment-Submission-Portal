# 7. Cloud storage design

## 7.1 Cloud database vs cloud object storage

| | Cloud database (PostgreSQL) | Cloud object storage (S3-compatible) |
|---|---|---|
| Data shape | Structured rows and columns, relations | Unstructured blobs (bytes) + small metadata |
| Access | SQL queries, joins, transactions | HTTP: PUT / GET / DELETE an object by key |
| Good at | Filtering, counting, integrity constraints | Storing huge amounts of files cheaply and durably |
| Size per item | Bytes to KB per row | KB to TB per object |
| Scaling | Vertical + read replicas | Practically unlimited, automatic |
| Cost | Higher per GB | Very low per GB |
| In this project | users, courses, enrollments, assignments, deadlines, **submission metadata**, marks, feedback, audit logs | PDF, DOCX, PPTX, ZIP, PNG/JPG, TXT/PY/IPYNB submissions |

The two are linked by the **object key** stored in `submissions.storage_path`.

## 7.2 Bucket structure

```
<bucket: assignment-submissions>            (private, no public access)
└── assignments/
    ├── assignment_001/
    │   ├── student_003/
    │   │   └── 20260925T101500Z_3f9a1c2e.pdf
    │   └── student_004/
    │       └── 20260925T113012Z_9b7d0e41.pdf
    └── assignment_002/
        └── student_003/
            └── 20260926T080102Z_c01d5aa7.zip
```

Built by `build_storage_path()` in `backend/services/submission_service.py`.

## 7.3 File naming and unique IDs

| Part | Example | Why |
|---|---|---|
| `assignment_{id:03d}` | `assignment_001` | Groups all work for one assignment, easy to list or export by prefix |
| `student_{id:03d}` | `student_003` | Groups one student's attempts; IDs, not names (privacy, no special characters) |
| UTC timestamp | `20260925T101500Z` | Sortable; tells you when the attempt was stored |
| Random ID | `3f9a1c2e` (UUID4 fragment) | Two uploads in the same second never collide; keys cannot be guessed |
| Extension | `.pdf` | From the **validated** extension, never from raw user input |

The user's original filename is **sanitized** (`sanitize_filename`: path parts, control characters and odd symbols removed) and kept only in `submissions.file_name` for display and as the download name. It never becomes part of the key, which prevents path traversal (`../../`) and header injection.

## 7.4 Operations

| Operation | Code | Notes |
|---|---|---|
| **Upload** | `storage.upload(key, bytes, content_type)` | S3 `put_object` with `ContentType`, `Metadata.sha256`, optional `ServerSideEncryption=AES256`. Local: write `.part` then atomic rename. Retried 3× with exponential backoff |
| **Download** | `storage.generate_signed_url(key, name, disposition, expires)` | Browser fetches directly from storage; `inline` opens the PDF, `attachment` downloads |
| **Delete** | `storage.delete(key)` | On resubmission (old attempt), on assignment delete with `force=true`, and as compensation when the DB write fails |
| **Exists / health** | `storage.exists`, `storage.health_check` | Download pre-check; `/api/health` uses `head_bucket` |

## 7.5 Signed / private URLs

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as API
    participant S as Object storage
    B->>A: GET /api/submissions/42/download  (JWT)
    A->>A: is B the owner / course teacher / admin?
    A->>A: sign(key, expiry = now + 300 s)
    A-->>B: {url: "https://bucket…/key?X-Amz-Expires=300&X-Amz-Signature=…"}
    B->>S: GET url  (no JWT needed; the signature is the permission)
    S->>S: signature valid and not expired?
    S-->>B: file bytes
```

* **S3 provider**: real AWS SigV4 pre-signed URL (`generate_presigned_url`).
* **Local provider**: `/api/files/signed?path&expires&name&disposition&signature`, where the signature is `HMAC-SHA256(SECRET_KEY, path|expires|name|disposition)`. Changing any parameter or waiting past `expires` → `403`.
* A leaked link works for at most `SIGNED_URL_EXPIRE_SECONDS` (default 300).

## 7.6 Access permissions

| Layer | Setting |
|---|---|
| Bucket policy | **Block all public access**. No public-read ACLs |
| Credentials | Only the backend has keys (env vars / IAM role). The browser never gets storage credentials |
| Least privilege (AWS IAM policy for the backend) | `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` on `arn:aws:s3:::assignment-submissions/assignments/*`, plus `s3:ListBucket` for health |
| Encryption | In transit: HTTPS. At rest: SSE-S3/SSE-KMS (AWS), default encryption (Supabase/R2) |
| App-level | Signed URLs are only issued after the RBAC and ownership checks in section 8 |

Example IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::assignment-submissions/assignments/*" },
    { "Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": "arn:aws:s3:::assignment-submissions" }
  ]
}
```

## 7.7 Provider configuration cheat-sheet

| Provider | `S3_ENDPOINT_URL` | `S3_REGION` | Keys from |
|---|---|---|---|
| AWS S3 | *(empty)* | e.g. `ap-south-1` | IAM user or role |
| Supabase Storage | `https://<project-ref>.supabase.co/storage/v1/s3` | your project region | Project Settings → Storage → S3 access keys |
| Cloudflare R2 | `https://<account-id>.r2.cloudflarestorage.com` | `auto` | R2 → Manage API tokens |
| MinIO (docker-compose) | `http://storage:9000` (+ `S3_PUBLIC_ENDPOINT_URL=http://localhost:9000`) | `us-east-1` | compose file |
