# Screenshots (proof of work)

Put your PNG screenshots in this folder using exactly these names so the README and report links work. Use only the **fictional demo data** from `python -m backend.seed`. Crop out personal bookmarks and tabs, and never show `.env` contents, access keys or passwords.

| # | File name | What to capture | What it proves |
|---|---|---|---|
| 1 | `01_project_folder_structure.png` | VS Code explorer: `backend/`, `cloud/`, `frontend/src/`, `tests/`, `docs/` expanded | Organized, layered codebase |
| 2 | `02_architecture_diagram.png` | Architecture diagram in the README on GitHub | Cloud architecture design |
| 3 | `03_login_page.png` | `/login` | Authentication UI |
| 4 | `04_student_registration.png` | `/register` filled with a fictional student | Self-registration (student role only) |
| 5 | `05_teacher_dashboard.png` | `/teacher` as `meera.iyer@portal.dev` | Aggregated cloud-DB statistics |
| 6 | `06_assignment_creation.png` | `/assignments/new` filled in | Teacher can create assignments with rules |
| 7 | `07_student_dashboard.png` | `/student` as `priya@portal.dev` | Role-based dashboard |
| 8 | `08_assignment_list.png` | `/assignments` (student view with stamps) | Assignment retrieval by enrollment |
| 9 | `09_assignment_details.png` | `/assignments/{id}` top half | Deadline, file rules, policies |
| 10 | `10_file_selection_screen.png` | Drop zone showing a selected PDF | Client-side validation / upload UI |
| 11 | `11_successful_upload.png` | Green "Submission received" + SUBMITTED stamp | Upload to cloud storage succeeded |
| 12 | `12_cloud_storage_file.png` | Object in MinIO console / Supabase Storage / `storage_data` tree | File lives in object storage under `assignments/assignment_xxx/student_xxx/` |
| 13 | `13_database_submission_record.png` | `submissions` table row with `storage_path` | Metadata in the cloud DB links to the object |
| 14 | `14_on_time_submission_status.png` | SUBMITTED stamp + received time | Server-side on-time decision |
| 15 | `15_late_submission_demo.png` | LATE stamp + "recorded as LATE" message (or 403 when late work is disabled) | Deadline logic works |
| 16 | `16_teacher_submission_list.png` | Assignment → Submissions roster | Central tracking incl. NOT SUBMITTED |
| 17 | `17_teacher_reviewing_file.png` | PDF opened in a new tab, address bar showing `signature=`/`X-Amz-Signature=` | Private files via signed URLs |
| 18 | `18_marks_and_feedback.png` | Grade form with "Grade saved" | Grading workflow |
| 19 | `19_student_feedback_page.png` | Student's submission page with red-pen grade and feedback | Feedback reaches the student |
| 20 | `20_authorization_error_demo.png` | Student visiting `/teacher` (403 page) or Swagger 403 JSON | RBAC enforced |
| 21 | `21_api_response.png` | Swagger `/docs` showing a 200 response | REST API |
| 22 | `22_automated_tests.png` | Terminal: `pytest -v` → `67 passed` | Tested, including failure scenarios |
| 23 | `23_cloud_deployment_dashboard.png` | Render service "Live" + Vercel deployment "Ready" | Cloud deployment |
| 24 | `24_live_application.png` | App at your public HTTPS URL | Accessible from anywhere |
| 25 | `25_github_commits.png` | GitHub commit history | Incremental development |
| 26 | `26_github_repository.png` | Repo homepage: description, topics, green CI badge | Professional repo |
| 27 | `27_readme_preview.png` | Rendered README | Documentation quality |

Tips: Windows `Win + Shift + S`, macOS `Cmd + Shift + 4`. Use a 1366×768 or 1440×900 browser window for consistent images, and take a light-mode and dark-mode shot of the dashboards if you like.
