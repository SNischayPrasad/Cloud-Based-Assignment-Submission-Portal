# 14. REST API reference

* Base URL (local): `http://localhost:8000/api`. Interactive Swagger UI: `http://localhost:8000/docs`
* Auth header: `Authorization: Bearer <access_token>` (from `POST /api/login`)
* Every error uses one JSON shape:

```json
{ "detail": "Human readable message", "code": "MACHINE_READABLE_CODE" }
```

| Status | Meaning in this API |
|---|---|
| 200 OK | Read / update succeeded (also a resubmission or idempotent replay) |
| 201 Created | New user, course, assignment or first submission |
| 400 Bad Request | Business-rule validation failed (past deadline, marks > max, empty file…) |
| 401 Unauthorized | Missing / invalid / expired / revoked token, or wrong credentials |
| 403 Forbidden | Authenticated but not allowed (wrong role, not your course, not your submission, deadline closed) |
| 404 Not Found | Resource does not exist |
| 409 Conflict | Duplicate (email, course code, submission, already graded) |
| 413 Payload Too Large | File bigger than the assignment limit |
| 415 Unsupported Media Type | File extension not allowed or content does not match the extension |
| 422 Unprocessable Entity | Request body/params fail schema validation |
| 429 Too Many Requests | Login/register rate limit hit |
| 503 Service Unavailable | Database or object storage temporarily down |

---

## AUTH

### POST /api/register
| | |
|---|---|
| Request | `{"name": "Aarav Sharma", "email": "aarav@portal.dev", "password": "Student123"}` |
| Authentication | none (rate-limited per IP) |
| Authorization | public; **always creates a student** |
| Response 201 | `{"user_id": 8, "name": "Aarav Sharma", "email": "aarav@portal.dev", "role": "student", "is_active": true, "created_at": "…Z"}` |
| Errors | 409 `EMAIL_EXISTS`, 422 weak password / bad email, 429 `RATE_LIMITED` |

### POST /api/login
| | |
|---|---|
| Request | `{"email": "meera.iyer@portal.dev", "password": "••••••••"}` |
| Authentication | none (rate-limited) |
| Response 200 | see below |
| Errors | 401 `INVALID_CREDENTIALS` (same for unknown email and wrong password), 401 `ACCOUNT_DISABLED`, 429 |

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": { "user_id": 2, "name": "Dr. Meera Iyer", "email": "meera.iyer@portal.dev",
            "role": "teacher", "is_active": true, "created_at": "2026-09-25T03:05:23Z" }
}
```

### POST /api/logout
| | |
|---|---|
| Request | no body |
| Authentication | Bearer token |
| Response 200 | `{"message": "Logged out. This token can no longer be used."}` |
| Errors | 401 if the token is already invalid. Afterwards any use of the token → 401 `TOKEN_REVOKED` |

### GET /api/me
Returns the current user (200) or 401. Used by the frontend to validate a stored session.

---

## COURSES

| Method & path | Auth | Authorization | Request | Response |
|---|---|---|---|---|
| `GET /api/courses` | Bearer | any role (scoped) | – | 200 list of `{course_id, course_code, course_name, teacher_name, join_code*, student_count, assignment_count}`. *`join_code` only for owner/admin* |
| `POST /api/courses` | Bearer | teacher (admin must pass `teacher_id`) | `{"course_code": "CC401", "course_name": "Cloud Computing", "description": ""}` | 201 course. 409 `COURSE_EXISTS` |
| `POST /api/courses/join` | Bearer | student | `{"join_code": "CLOUD4"}` | 201 course. 404 `BAD_JOIN_CODE`, 409 `ALREADY_ENROLLED` |
| `GET /api/courses/{id}/students` | Bearer | course teacher / admin | – | 200 roster. 403 `COURSE_FORBIDDEN` |
| `POST /api/courses/{id}/students` | Bearer | course teacher / admin | `{"email": "sara@portal.dev"}` | 201. 404 if no such student, 409 if already enrolled |

---

## ASSIGNMENTS

### POST /api/assignments (createAssignment)
| | |
|---|---|
| Authentication | Bearer |
| Authorization | teacher who owns `course_id`, or admin |
| Request | see below |
| Response 201 | the assignment (`AssignmentOut`) |
| Errors | 400 past deadline / type not allowed on portal / size above portal limit, 403 `ROLE_FORBIDDEN` or `COURSE_FORBIDDEN`, 404 course, 422 schema (title < 3 chars, max_marks ≤ 0 …) |

```json
{
  "course_id": 1,
  "title": "Serverless Function Lab",
  "description": "Deploy a small HTTP function…",
  "deadline": "2026-10-10T11:30:00Z",
  "max_marks": 25,
  "allowed_file_types": ["pdf", "docx"],
  "max_file_size_mb": 10,
  "allow_late_submission": true,
  "allow_resubmission": true
}
```

Response (`GET /api/assignments/1` as the teacher):

```json
{
  "assignment_id": 1, "course_id": 1, "course_code": "CC401", "course_name": "Cloud Computing",
  "title": "Design a Three-Tier Cloud Architecture",
  "description": "Draw and explain a three-tier web architecture…",
  "deadline": "2026-10-02T18:30:00Z", "max_marks": 20.0,
  "allowed_file_types": ["pdf", "docx"], "max_file_size_mb": 10,
  "allow_late_submission": true, "allow_resubmission": true,
  "created_by": 2, "created_at": "2026-09-25T03:05:23Z", "updated_at": "2026-09-25T03:05:23Z",
  "is_past_deadline": false,
  "my_status": null, "my_submission_id": null,
  "submission_count": 0, "enrolled_count": 4
}
```

For a **student**, `my_status` is `NOT_SUBMITTED | SUBMITTED | LATE | GRADED` and the counts are `null`.

### GET /api/assignments (getAssignments)
Query: `course_id` (optional). Student: assignments of enrolled courses. Teacher: owned courses. Admin: all. 200 list, 401.

### GET /api/assignments/{id} (getAssignmentById)
200, 401, 403 `NOT_ENROLLED` / `COURSE_FORBIDDEN`, 404.

### PUT /api/assignments/{id} (updateAssignment)
Partial update. Any subset of the create fields except `course_id`. 200 updated assignment. 400 if the new deadline is in the past or `max_marks` is below a mark already awarded. 403 if not the course teacher. 404.

### DELETE /api/assignments/{id}?force=false (deleteAssignment)
200 `{"message": "Assignment deleted.", "files_removed": 3}`. **409 `HAS_SUBMISSIONS`** if submissions exist and `force` is false. 403, 404.

---

## SUBMISSIONS

### POST /api/assignments/{id}/submit (submitAssignment / resubmitAssignment)
| | |
|---|---|
| Content type | `multipart/form-data` with field `file` |
| Optional header | `Idempotency-Key: <uuid>`, the same key for retries of the same attempt |
| Authentication | Bearer |
| Authorization | student enrolled in the assignment's course |
| Response 201 | first submission |
| Response 200 | resubmission (file replaced, `attempt_number` + 1) or idempotent replay (`replayed: true`) |
| Errors | 403 `NOT_ENROLLED`, 403 `DEADLINE_PASSED` (late not allowed), 409 `DUPLICATE_SUBMISSION` (resubmission disabled or race), 409 `ALREADY_GRADED`, 413 `FILE_TOO_LARGE`, 415 `UNSUPPORTED_FILE_TYPE` (extension or content mismatch), 400 empty file, 503 `STORAGE_UNAVAILABLE` / `DATABASE_UNAVAILABLE` (nothing saved) |

```bash
curl -X POST http://localhost:8000/api/assignments/1/submit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: 6f1c6c1e-2b8e-4a55-9d0e-2e6f3c1d7a10" \
  -F "file=@sample_files/sample_assignment.pdf"
```

```json
{
  "submission": { "submission_id": 5, "submission_status": "SUBMITTED", "is_late": false,
                  "attempt_number": 1, "file_name": "sample_assignment.pdf",
                  "storage_path": "assignments/assignment_001/student_005/20260925T030727Z_0a4cda8b.pdf", "…": "…" },
  "message": "Submission received.",
  "replayed": false
}
```

### GET /api/submissions/me (getMySubmissions)
Student only. 200 list of `SubmissionOut`, newest first. 403 for other roles.

### GET /api/assignments/{id}/submissions
Course teacher / admin. Every enrolled student with status (including `NOT_SUBMITTED`) plus a summary:

```json
{ "assignment_id": 3, "assignment_title": "Virtualization vs Containers Report", "max_marks": 10.0,
  "deadline": "2026-09-23T18:30:00Z",
  "summary": {"enrolled": 4, "submitted": 3, "not_submitted": 1, "on_time": 2, "late": 1, "graded": 2, "pending_review": 1},
  "entries": [ {"student_id": 6, "student_name": "Rahul Verma", "status": "SUBMITTED", "submission": {"…": "…"}},
               {"student_id": 7, "student_name": "Sara Khan", "status": "NOT_SUBMITTED", "submission": null} ] }
```

### GET /api/submissions/{id}
Owner student, course teacher or admin. 200 `SubmissionOut`:

```json
{
  "submission_id": 3, "assignment_id": 3, "assignment_title": "Virtualization vs Containers Report",
  "course_code": "CC401", "deadline": "2026-09-23T18:30:00Z", "max_marks": 10.0,
  "student_id": 6, "student_name": "Rahul Verma", "student_email": "rahul@portal.dev",
  "file_name": "rahul_3.pdf", "file_size": 697, "content_type": "application/pdf",
  "file_url": "local://assignments/assignment_003/student_006/20260923T153000Z_ba98559f.pdf",
  "storage_path": "assignments/assignment_003/student_006/20260923T153000Z_ba98559f.pdf",
  "checksum_sha256": "ec033f8c7277ac95ac8a488ab659274f0bb2b3a49b7304c166f410cb0c8c87c9",
  "submitted_at": "2026-09-23T15:30:00Z", "submission_status": "SUBMITTED", "is_late": false,
  "attempt_number": 1, "marks": null, "feedback": null, "graded_at": null, "can_resubmit": true
}
```
Errors: 403 `SUBMISSION_FORBIDDEN` (another student's), 403 `COURSE_FORBIDDEN` (other teacher), 404.

---

## FEEDBACK

### POST /api/submissions/{id}/grade (gradeSubmission)
| | |
|---|---|
| Request | `{"marks": 17.5, "feedback": "Good diagram. Explain autoscaling triggers."}` |
| Authentication | Bearer |
| Authorization | teacher of the course, or admin (students → 403 `ROLE_FORBIDDEN`, other teachers → 403 `GRADE_FORBIDDEN`) |
| Response 200 | updated `SubmissionOut` with `submission_status: "GRADED"` |
| Errors | 400 `MARKS_EXCEED_MAXIMUM` (`"Marks (99) cannot exceed the maximum of 10 for this assignment."`), 422 negative marks / feedback > 5000 chars, 404 |

### GET /api/submissions/{id}/feedback (getSubmissionFeedback)
Owner student, course teacher or admin.

```json
{ "submission_id": 2, "assignment_id": 3, "assignment_title": "Virtualization vs Containers Report",
  "submission_status": "GRADED", "is_late": true, "marks": 6.5, "max_marks": 10.0,
  "feedback": "Submitted 5 hours late. Content is correct but …",
  "graded_at": "2026-09-24T23:30:00Z", "graded_by_name": "Dr. Meera Iyer" }
```
Before grading, `marks`, `feedback` and `graded_at` are `null`.

---

## FILES

### GET /api/submissions/{id}/download?disposition=attachment|inline
| | |
|---|---|
| Authentication | Bearer |
| Authorization | owner student, course teacher, admin |
| Response 200 | `{"url": "<signed url>", "expires_in": 300, "file_name": "rahul_3.pdf", "disposition": "attachment"}` |
| Errors | 401, 403, 404 `FILE_MISSING`, 503 `STORAGE_UNAVAILABLE` |

With S3 the `url` is an AWS SigV4 pre-signed URL. With local storage it is:
`http://localhost:8000/api/files/signed?path=assignments%2F…pdf&expires=1790306613&name=rahul_3.pdf&disposition=attachment&signature=05418b7f…`

### GET /api/files/signed (local provider only)
No JWT: the HMAC signature is the permission. 200 file stream (`Cache-Control: private, no-store`). 403 `LINK_EXPIRED` if tampered or expired. 404 with the S3 provider.

---

## DASHBOARDS, ADMIN, HEALTH

| Method & path | Authorization | Response |
|---|---|---|
| `GET /api/dashboard/student` | student | `{student_name, stats{courses,total_assignments,pending_assignments,overdue_assignments,submitted_assignments,late_assignments,graded_assignments,average_percentage}, upcoming_deadlines[], recent_feedback[]}` |
| `GET /api/dashboard/teacher` | teacher / admin | `{teacher_name, stats{courses,total_assignments,total_students,total_submissions,pending_reviews,late_submissions,graded_submissions}, recent_uploads[], upcoming_deadlines[]}` |
| `GET /api/admin/users?role=` | admin | list of users |
| `POST /api/admin/users` | admin | `{name,email,password,role}` → 201 |
| `PATCH /api/admin/users/{id}` | admin | `{role?, is_active?, name?}`. Cannot demote or disable yourself (403) |
| `GET /api/admin/audit-logs?limit=&action=` | admin | recent audit events |
| `GET /api/health` | public | 200 `ok` / 503 `degraded`, see below |

```json
{ "status": "ok", "environment": "development",
  "checks": { "database": {"ok": true, "dialect": "sqlite"}, "object_storage": {"ok": true, "provider": "local"} },
  "metrics": { "uptime_seconds": 763, "requests_total": 67, "responses_4xx": 6, "responses_5xx": 0, "avg_latency_ms": 71.47 } }
```

Every response also carries an `X-Request-ID` header, which you can use to find the matching server log line.
