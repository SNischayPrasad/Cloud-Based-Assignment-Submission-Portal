# 20. Testing strategy

## Levels of testing

| Level | Tool | What |
|---|---|---|
| Unit | pytest (`tests/test_units.py`) | password hashing, JWT, filename sanitizing, file validation, deadline policy incl. timezones |
| API / integration | pytest + FastAPI `TestClient` | every endpoint through HTTP with a real (temporary) SQLite DB and real local object storage |
| Fault injection | pytest `monkeypatch` | storage outage, flaky storage, DB failure after upload, DB down on read, degraded health |
| Cloud provider | pytest + **moto** (fake AWS S3) | S3 upload/download/delete, SSE header, pre-signed URL expiry, health |
| Manual / UI | browser | the 18-step walkthrough in [08-local-setup.md](08-local-setup.md) |
| CI | GitHub Actions | tests + frontend build + Docker build on every push |

Run everything:

```bash
pytest -v                       # 67 tests
pytest tests/test_failures.py -v    # only the cloud-failure scenarios
```

Each test gets an **empty temporary database and storage folder** (`tests/conftest.py`), so tests never touch your real data and can run in any order.

## Test cases

"Actual result" and "Pass/Fail" below were recorded by running the automated suite (67/67 passed) and the manual browser walkthrough while building the project. **Re-run them yourself and update this table** with your own results and screenshots before submitting.

| Test ID | Scenario | Input | Expected result | Actual result | Pass/Fail | Automated test |
|---|---|---|---|---|---|---|
| TC-01 | Student registration | `POST /api/register` name, email (mixed case), valid password | 201, role = student, email lower-cased, no password in response | 201, role `student`, `aarav@portal.dev` | ✅ Pass | `test_tc01_student_registration` |
| TC-02 | Teacher login | teacher email + correct password | 200 with JWT, `user.role = teacher`, `expires_in > 0` | 200, token issued, role `teacher` | ✅ Pass | `test_tc02_teacher_login` |
| TC-03 | Invalid login | wrong password; unknown email | 401 with identical message for both | 401 `Incorrect email or password.` for both | ✅ Pass | `test_tc03_invalid_login` |
| TC-04 | Student dashboard authorization | student token → `/api/dashboard/student`, then `/teacher` | 200 with correct counts; teacher dashboard 403 | 200 (2 total, 1 pending, 1 submitted); 403 | ✅ Pass | `test_tc04_student_dashboard_authorization` |
| TC-05 | Teacher dashboard authorization | teacher token → `/teacher`; other teacher; teacher → `/student` | own stats only; other teacher sees 0; student dashboard 403 | as expected | ✅ Pass | `test_tc05_teacher_dashboard_authorization` |
| TC-06 | Teacher creates assignment | valid payload, types `"PDF, .docx"` | 201, types normalized to `["pdf","docx"]`, enrolled_count 2 | 201, normalized | ✅ Pass | `test_tc06_teacher_creates_assignment` |
| TC-07 | Student views assignment | enrolled student lists + opens it | listed with `my_status = NOT_SUBMITTED`, details 200 | as expected | ✅ Pass | `test_tc07_student_views_assignment` |
| TC-08 | Valid PDF upload | `report.pdf` (real PDF bytes) | 201, object stored under `assignments/assignment_xxx/student_xxx/`, bytes identical, DB row exists | 201, byte-for-byte match, row present | ✅ Pass | `test_tc08_valid_pdf_upload_and_tc11_on_time` |
| TC-09 | Invalid file extension | `virus.exe` | 415, nothing stored | 415 | ✅ Pass | `test_tc09_invalid_extension` (+ `test_renamed_file_rejected_by_content_check`) |
| TC-10 | Oversized file | 1 MB + 10 bytes on a 1 MB assignment | 413 | 413 `FILE_TOO_LARGE` | ✅ Pass | `test_tc10_oversized_file` |
| TC-11 | On-time submission | upload before deadline | status SUBMITTED, `is_late = false` | SUBMITTED | ✅ Pass | `test_tc08_…_and_tc11_on_time` |
| TC-12 | Late submission | server clock +30 h past deadline, late allowed / not allowed | LATE + message / 403 `DEADLINE_PASSED` | LATE / 403 | ✅ Pass | `test_tc12_late_submission_recorded_as_late`, `test_late_submission_blocked_when_disabled` |
| TC-13 | Resubmission | second upload | 200, same submission id, attempt 2, new object stored, old object deleted | as expected | ✅ Pass | `test_tc13_resubmission_replaces_file` (+ disabled → 409) |
| TC-14 | Student views own submission | `GET /api/submissions/me` | 1 item for owner, empty for other student | as expected | ✅ Pass | `test_tc14_student_views_own_submissions` |
| TC-15 | Student cannot view another student's submission | other student → details, feedback, download | 403 on all three | 403 ×3 | ✅ Pass | `test_tc15_student_cannot_view_another_students_submission` |
| TC-16 | Teacher views submissions | `GET /api/assignments/{id}/submissions` | roster with SUBMITTED + NOT_SUBMITTED, summary counts | enrolled 2, submitted 1, not submitted 1 | ✅ Pass | `test_tc16_teacher_views_submissions` |
| TC-17 | Teacher grades submission | marks 17.5, feedback with spaces | 200, GRADED, feedback trimmed | as expected | ✅ Pass | `test_tc17_teacher_grades_and_tc19_student_views_feedback` |
| TC-18 | Marks above maximum rejected | marks 25 on max 20; marks −1 | 400 `MARKS_EXCEED_MAXIMUM`; 422 | 400; 422 | ✅ Pass | `test_tc18_marks_above_maximum_rejected` |
| TC-19 | Student views feedback | owner → `/feedback` | marks, max, feedback, grader name | 17.5/20, "Dr. Test Teacher" | ✅ Pass | `test_tc17_…_and_tc19_…` |
| TC-20 | Unauthorized grading rejected | student grades; other teacher grades | 403, 403, marks unchanged | 403, 403, marks `null` | ✅ Pass | `test_tc20_unauthorized_grading_rejected` |
| TC-21 | File retrieval | student and teacher request download URL and fetch it without a JWT | 200 signed URL, file bytes match, `attachment` disposition | as expected | ✅ Pass | `test_tc21_file_retrieval_via_signed_url` (+ tampered/expired → 403) |
| TC-22 | Cloud-storage failure | storage `upload` raises every time | 3 attempts, then 503 `STORAGE_UNAVAILABLE`, 0 DB rows | 3 attempts, 503, 0 rows | ✅ Pass | `test_tc22_storage_failure_returns_503_and_saves_nothing` (+ transient failure retried → 201) |
| TC-23 | Database failure | DB commit fails after the file was uploaded | 503 `DATABASE_UNAVAILABLE`, uploaded object deleted | 503, storage empty | ✅ Pass | `test_tc23_database_failure_after_upload_cleans_up_file` (+ DB down on read → 503) |
| TC-24 | Logout | `POST /api/logout` | 200 | 200 | ✅ Pass | `test_tc24_logout_and_tc25_protected_route_after_logout` |
| TC-25 | Protected route after logout | reuse old token on `/api/me`; open `/teacher` in UI after logout | 401 `TOKEN_REVOKED`; UI redirects to login | 401 `TOKEN_REVOKED` | ✅ Pass | same test |

### Additional automated checks

| Area | Tests |
|---|---|
| Security | role escalation on register ignored · weak password 422 · duplicate email 409 · disabled account token rejected · login rate limit 429 · unauthenticated download 401 · tampered/expired signed URL 403 · role change applied instantly |
| Assignments | past deadline 400 · disallowed type 400 · zero marks 422 · size over portal limit 400 · short title 422 · update by other teacher 403 · delete with submissions needs `force` · non-enrolled student 403 |
| Submissions | empty file 400 · renamed text file as PDF 415 · teacher cannot submit 403 · idempotent retry returns original (attempt stays 1) · resubmission disabled 409 · graded work cannot be replaced 409 · `is_late` survives grading |
| Courses/admin | join by code (case-insensitive), wrong code 404, duplicate join 409 · students never see join codes · teacher creates course · admin-only endpoints 403 for others · audit log contains LOGIN_SUCCESS/USER_CREATED |
| Ops | `/api/health` 200 with request-ID and security headers; 503 when storage is degraded |
| S3 (moto) | upload/download/delete, `ServerSideEncryption=AES256`, checksum metadata, pre-signed URL has expiry + signature + content-disposition |

## Sample output

```
$ pytest -v
tests/test_assignments.py::test_tc06_teacher_creates_assignment PASSED
tests/test_auth.py::test_tc01_student_registration PASSED
…
tests/test_failures.py::test_tc22_storage_failure_returns_503_and_saves_nothing PASSED
tests/test_failures.py::test_tc23_database_failure_after_upload_cleans_up_file PASSED
tests/test_s3_storage.py::test_presigned_url_is_private_and_expiring PASSED
…
============================== 67 passed in ~20s ===============================
```

## How fault injection works (explain this in viva)

```python
def broken_upload(self, path, data, content_type):
    raise StorageError("simulated outage")
monkeypatch.setattr(LocalStorageService, "upload", broken_upload)
```
The test replaces the storage method with one that always fails. It then checks that the API retried three times, answered 503 and wrote **no** database row. The DB test does the reverse: the upload succeeds, the commit fails, and the test checks that the orphan object was deleted.
