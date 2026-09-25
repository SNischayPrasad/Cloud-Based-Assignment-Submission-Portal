# 24, 26 & 27. GitHub upload, proof-building plan and screenshot checklist

## 24. GitHub upload strategy

**Repository name:** `Cloud-Based-Assignment-Submission-Portal`

**Description:**
> Cloud-based student assignment submission and feedback platform featuring role-based authentication, cloud database integration, object storage, assignment management, secure file submission, grading, and feedback workflows.

**Topics:** `cloud-computing` `edtech` `python` `fastapi` `flask` `react` `cloud-storage` `firebase` `database` `rest-api` `full-stack` `authentication`
(Suggested extras that match the code: `postgresql` `aws-s3` `supabase` `jwt` `docker` `github-actions`. You can drop `flask`/`firebase` since the project uses FastAPI and S3-compatible storage, which keeps the topics honest.)

### One-time setup

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```
Create an **empty** repository on github.com (no README/license, since we already have them). Then:

```bash
cd Cloud-Based-Assignment-Submission-Portal
git init
git branch -M main
git remote add origin https://github.com/SNischayPrasad/Cloud-Based-Assignment-Submission-Portal.git
```

**Before the first commit, make sure no secrets are staged:**
```bash
git status --ignored          # .env, portal.db, storage_data/, .venv/, node_modules/ must be under "Ignored"
```

### Recommended commits (each adds the files for that step)

```bash
git add .gitignore .env.example README.md requirements.txt requirements-dev.txt pytest.ini
git commit -m "Initialize cloud assignment portal"

git add backend/__init__.py backend/app.py backend/config.py backend/routes/__init__.py backend/routes/health.py backend/utils/__init__.py backend/utils/logging_config.py backend/utils/errors.py frontend/package.json frontend/package-lock.json frontend/vite.config.js frontend/index.html frontend/public frontend/.env.example frontend/src/main.jsx frontend/src/App.jsx frontend/src/styles
git commit -m "Create frontend and backend architecture"

git add cloud/__init__.py cloud/auth_service.py backend/middleware backend/schemas/__init__.py backend/schemas/auth.py backend/schemas/user.py backend/schemas/validation.py backend/services/__init__.py backend/services/user_service.py backend/routes/auth.py backend/routes/admin.py frontend/src/context frontend/src/components/ProtectedRoute.jsx frontend/src/components/Layout.jsx frontend/src/pages/AuthShell.jsx frontend/src/pages/LoginPage.jsx frontend/src/pages/RegisterPage.jsx frontend/src/pages/ForbiddenPage.jsx frontend/src/pages/NotFoundPage.jsx frontend/src/pages/AdminPage.jsx frontend/src/services/api.js frontend/src/services/authService.js frontend/src/services/adminService.js
git commit -m "Implement authentication and role management"

git add backend/schemas/course.py backend/schemas/assignment.py backend/services/course_service.py backend/services/assignment_service.py backend/routes/courses.py backend/routes/assignments.py frontend/src/pages/AssignmentsPage.jsx frontend/src/pages/AssignmentFormPage.jsx frontend/src/pages/CoursesPage.jsx frontend/src/services/assignmentService.js frontend/src/services/courseService.js frontend/src/hooks frontend/src/components/ui.jsx frontend/src/utils
git commit -m "Add assignment management module"

git add cloud/database_service.py backend/models backend/seed.py backend/utils/pdf_builder.py
git commit -m "Integrate cloud database"

git add cloud/storage_service.py backend/routes/files.py backend/utils/retry.py docker-compose.yml
git commit -m "Implement cloud file storage"

git add backend/schemas/submission.py backend/services/submission_service.py backend/utils/validators.py backend/utils/audit.py frontend/src/components/FileDropzone.jsx frontend/src/pages/AssignmentDetailPage.jsx frontend/src/pages/MySubmissionsPage.jsx frontend/src/services/submissionService.js scripts sample_files
git commit -m "Add student assignment submission workflow"

git add backend/services/deadline_policy.py backend/utils/time_utils.py
git commit -m "Implement deadline validation"

git add backend/services/grading_service.py backend/routes/submissions.py frontend/src/pages/SubmissionPage.jsx
git commit -m "Add teacher grading and feedback"

git add backend/services/dashboard_service.py backend/routes/dashboard.py frontend/src/pages/StudentDashboard.jsx frontend/src/pages/TeacherDashboard.jsx frontend/src/services/dashboardService.js
git commit -m "Build student and teacher dashboards"

git add docs/11-security.md
git commit -m "Add security and authorization"

git add tests .github
git commit -m "Add automated tests"

git add Dockerfile .dockerignore render.yaml backend/lambda_handler.py frontend/vercel.json frontend/netlify.toml docs/09-cloud-deployment.md
git commit -m "Deploy application to cloud"

git add docs reports screenshots README.md
git commit -m "Complete README and documentation"

git status            # should say "nothing to commit, working tree clean"
git push -u origin main
```

If a commit reports "nothing added", the files already went into an earlier commit. That's fine; move on. `git add -A` at the end catches anything left over.

Then on GitHub: **About (⚙) → description, website (your Vercel URL), topics**. Pin the repo on your profile. Check the **Actions** tab to see CI passing.

> **Honest history matters.** Commit as you actually study, run and screenshot each module (the plan below). Don't fake commit dates with `GIT_AUTHOR_DATE`. Interviewers can see the timestamps, and being able to explain every module is what makes this proof of work.

---

## 26. Proof-building strategy (13 days)

Each day: read the files, run them, change something small so you understand it, take the screenshot, commit.

| Day | Focus | Files | Functionality | Commit | Screenshot | What it proves |
|---|---|---|---|---|---|---|
| 1 | Architecture + repo | README, `.gitignore`, `.env.example`, `requirements*.txt`, docs/07 | Repo, venv, dependency install, architecture diagram | `Initialize cloud assignment portal` | `01_project_folder_structure.png`, `02_architecture_diagram.png` | You planned a layered cloud design before coding |
| 2 | Authentication | `cloud/auth_service.py`, `routes/auth.py`, `services/user_service.py`, Login/Register pages | Register, login, JWT, logout revocation | `Implement authentication and role management` | `03_login_page.png`, `04_student_registration.png` | Working auth; passwords hashed |
| 3 | Role-based access | `middleware/auth.py`, `ProtectedRoute.jsx`, `routes/admin.py`, `AdminPage.jsx` | `require_roles`, 403 page, admin user management | (part of Day 2 commit or a follow-up) | `20_authorization_error_demo.png` | Server-side RBAC, not just hidden buttons |
| 4 | Assignment management | `assignment_service.py`, `routes/assignments.py`, `AssignmentFormPage.jsx`, `CoursesPage.jsx` | Courses, join codes, assignment CRUD + validation | `Add assignment management module` | `06_assignment_creation.png`, `08_assignment_list.png` | Teacher workflow and input validation |
| 5 | Cloud database | `cloud/database_service.py`, `models/*`, `seed.py` | Tables, keys, indexes; SQLite ↔ PostgreSQL via `DATABASE_URL` | `Integrate cloud database` | `13_database_submission_record.png` (DB browser or Supabase table editor) | Relational design, cloud-DB ready |
| 6 | Cloud object storage | `cloud/storage_service.py`, `routes/files.py`, `docker-compose.yml` | Local + S3 providers, signed URLs, private bucket | `Implement cloud file storage` | `12_cloud_storage_file.png` (MinIO/Supabase bucket or `storage_data` tree) | Files in object storage, not in the DB |
| 7 | Student submission | `submission_service.py`, `validators.py`, `FileDropzone.jsx`, `AssignmentDetailPage.jsx` | Upload, validation, retries, compensation, resubmission, idempotency | `Add student assignment submission workflow` | `10_file_selection_screen.png`, `11_successful_upload.png` | End-to-end upload into cloud storage |
| 8 | Deadline logic | `deadline_policy.py`, `time_utils.py` | Server-time on-time/late/blocked, timezone-safe | `Implement deadline validation` | `14_on_time_submission_status.png`, `15_late_submission_demo.png` | Correct, tamper-proof deadline handling |
| 9 | Teacher feedback | `grading_service.py`, `routes/submissions.py`, `SubmissionPage.jsx` | Review via signed URL, grade, feedback | `Add teacher grading and feedback` | `16_teacher_submission_list.png`, `17_teacher_reviewing_file.png`, `18_marks_and_feedback.png` | Complete grading loop with validation |
| 10 | Dashboards | `dashboard_service.py`, dashboard pages | Aggregate SQL, upcoming deadlines, recent feedback/uploads | `Build student and teacher dashboards` | `05_teacher_dashboard.png`, `07_student_dashboard.png`, `19_student_feedback_page.png` | Data-driven UI from cloud DB queries |
| 11 | Testing + security | `tests/*`, `.github/workflows/ci.yml`, docs/10, docs/11 | 67 tests incl. outage simulation; CI | `Add security and authorization`, `Add automated tests` | `21_api_response.png` (Swagger), `22_automated_tests.png` | Quality and security are verified, not claimed |
| 12 | Cloud deployment | `render.yaml`, `Dockerfile`, `vercel.json`, `lambda_handler.py`, docs/09 | Render + Vercel + Supabase live | `Deploy application to cloud` | `23_cloud_deployment_dashboard.png`, `24_live_application.png` | It really runs in the cloud with a public URL |
| 13 | Documentation | README, docs/*, report, screenshots | Final polish | `Complete README and documentation` | `25_github_commits.png`, `26_github_repository.png`, `27_readme_preview.png` | Professional presentation |

---

## 27. Screenshot / proof checklist

Save as PNG in `screenshots/`. Full list with capture tips: [../screenshots/README.md](../screenshots/README.md).

| # | File name | Capture |
|---|---|---|
| 1 | `01_project_folder_structure.png` | VS Code explorer with folders expanded |
| 2 | `02_architecture_diagram.png` | README architecture diagram rendered on GitHub |
| 3 | `03_login_page.png` | Login page |
| 4 | `04_student_registration.png` | Registration form filled (fictional name) |
| 5 | `05_teacher_dashboard.png` | Teacher dashboard with counts |
| 6 | `06_assignment_creation.png` | New-assignment form filled |
| 7 | `07_student_dashboard.png` | Student dashboard |
| 8 | `08_assignment_list.png` | Assignments page |
| 9 | `09_assignment_details.png` | Assignment detail with rules |
| 10 | `10_file_selection_screen.png` | Drop zone with a file selected |
| 11 | `11_successful_upload.png` | "Submission received" + SUBMITTED stamp |
| 12 | `12_cloud_storage_file.png` | Object in MinIO / Supabase bucket (or `storage_data` tree) |
| 13 | `13_database_submission_record.png` | `submissions` row (DB Browser for SQLite / Supabase table editor / psql) |
| 14 | `14_on_time_submission_status.png` | SUBMITTED stamp |
| 15 | `15_late_submission_demo.png` | LATE stamp + message |
| 16 | `16_teacher_submission_list.png` | Roster table with statuses |
| 17 | `17_teacher_reviewing_file.png` | PDF opened via signed URL (address bar shows the signature) |
| 18 | `18_marks_and_feedback.png` | Grade form saved |
| 19 | `19_student_feedback_page.png` | Student sees red-pen mark + feedback |
| 20 | `20_authorization_error_demo.png` | Student opening `/teacher` → 403 page, or Swagger 403 |
| 21 | `21_api_response.png` | Swagger `/docs` response |
| 22 | `22_automated_tests.png` | `pytest -v` → 67 passed |
| 23 | `23_cloud_deployment_dashboard.png` | Render/Vercel dashboard "Live" |
| 24 | `24_live_application.png` | App on the public URL |
| 25 | `25_github_commits.png` | Commit history |
| 26 | `26_github_repository.png` | Repo home with topics + green CI |
| 27 | `27_readme_preview.png` | Rendered README |
