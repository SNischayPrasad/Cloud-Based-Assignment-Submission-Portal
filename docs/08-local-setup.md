# 18. Local / virtual simulation: run everything for free

Two ways to run it without paid cloud infrastructure:

* **Path 1 (default):** SQLite + local folder storage. Only Python and Node are needed.
* **Path 2 (mini-cloud):** Docker Compose with **PostgreSQL + MinIO (S3 API)**, the same architecture as production.

Commands are shown for **Windows (PowerShell)** and **macOS/Linux** where they differ.

---

## Step 1: Install required software

| Tool | Version | Check |
|---|---|---|
| Python | 3.11 or newer | `python --version` → `Python 3.12.x` |
| Node.js | 20 or newer (includes npm) | `node --version` → `v22.x` |
| Git | any recent | `git --version` |
| Docker Desktop | optional (Path 2) | `docker --version` |
| VS Code | recommended | |

## Step 2: Get the code and create a virtual environment

```bash
git clone https://github.com/SNischayPrasad/Cloud-Based-Assignment-Submission-Portal.git
cd Cloud-Based-Assignment-Submission-Portal
python -m venv .venv
```
Activate it:
```powershell
.venv\Scripts\Activate.ps1          # Windows PowerShell
```
```bash
source .venv/bin/activate           # macOS / Linux
```
Expected: your prompt starts with `(.venv)`.

> PowerShell error "running scripts is disabled"? Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or call `.venv\Scripts\python.exe` directly.

## Step 3: Install backend dependencies

```bash
pip install -r requirements-dev.txt
```
Expected ending: `Successfully installed fastapi-… SQLAlchemy-… bcrypt-… PyJWT-… boto3-… pytest-…`

## Step 4: Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```
Expected: `added ~90 packages`.

> With npm 11+ you may see *"install scripts blocked … esbuild"*. The build still works because esbuild ships a prebuilt binary. To silence the warning, run `npm install-scripts approve esbuild`.

## Step 5: Configure `.env`

```bash
cp .env.example .env                       # Windows: copy .env.example .env
cp frontend/.env.example frontend/.env     # Windows: copy frontend\.env.example frontend\.env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
Edit `.env`:
```ini
SECRET_KEY=<paste the random value>
SEED_DEMO_PASSWORD=Demo@12345      # any password for the fictional demo accounts
```
Leave `DATABASE_URL=sqlite:///./portal.db` and `STORAGE_PROVIDER=local` for this path.

## Step 6: Start the backend

```bash
python -m backend.seed                               # optional: demo data
uvicorn backend.app:app --reload --port 8000
```
Expected seed output:
```
Demo data created (all names and emails are fictional).

Role     Email                       Name
admin    admin@portal.dev            Portal Admin
teacher  meera.iyer@portal.dev       Dr. Meera Iyer
teacher  daniel.brooks@portal.dev    Prof. Daniel Brooks
student  aarav@portal.dev            Aarav Sharma
student  priya@portal.dev            Priya Nair
student  rahul@portal.dev            Rahul Verma
student  sara@portal.dev             Sara Khan

Password for every demo account: Demo@12345
Course join codes: CC401 -> CLOUD4, DB302 -> DBSYS3
```
Expected server output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
... level=INFO logger=portal.database Database engine created (dialect=sqlite)
... level=INFO logger=portal.app Started Cloud Assignment Submission Portal (env=development, storage=local)
```
Check: open http://localhost:8000/api/health → `{"status":"ok", … "database":{"ok":true,"dialect":"sqlite"}, "object_storage":{"ok":true,"provider":"local"} …}` and http://localhost:8000/docs for Swagger.

## Step 7: Start the frontend (new terminal)

```bash
cd frontend
npm run dev
```
Expected: `VITE v5.x ready … ➜ Local: http://localhost:5173/`. Open it and you should see the **Handin** login page.

## Step 8: Create a teacher account

Teachers cannot self-register (by design). Choose one:
* **Seed** (Step 6) already created `meera.iyer@portal.dev`, or
* Log in as `admin@portal.dev` → **Users & audit** → *Create an account* → role **Teacher**, or
* Swagger: log in as admin → *Authorize* → `POST /api/admin/users` with `{"name":"Dr. Test Teacher","email":"teacher@portal.dev","password":"Teacher123","role":"teacher"}` → **201**.

If you created a new teacher, log in as them → **Courses** → **New course** (`CC401` / `Cloud Computing`) and note the **join code**.

## Step 9: Create a student account

Log out → **Create an account** → name, email (e.g. `student.one@portal.dev`), password `Student123` → you land on **Courses** → enter the join code (e.g. `CLOUD4`) → *Joined CC401 · Cloud Computing.*
API equivalent: `POST /api/register` → **201** with `"role": "student"`.

## Step 10: Teacher creates an assignment

Teacher → **New assignment** → course, deadline (for example tomorrow 17:00), title, instructions, marks 20, file types `.pdf`, size 10 MB → **Publish assignment**.
Expected: the assignment page opens; *Submissions* shows every enrolled student as **NOT SUBMITTED**.

## Step 11: Student logs in

Student dashboard shows *Welcome, …*, counts (Total / Pending / Submitted / Late / Graded) and the new assignment under **Upcoming deadlines**.

## Step 12: Student views the assignment

Click it to see the instructions, rules (types, size, late policy, resubmission) and the **Your submission** panel.

## Step 13: Student uploads the sample PDF

```bash
python scripts/generate_sample_files.py          # creates sample_files/*.pdf etc.
```
Drag `sample_files/sample_assignment.pdf` into the drop zone (or *Choose file*) → **Upload submission**.
Expected: progress bar → green *Submission received.* → **SUBMITTED** stamp, file name, size, attempt 1.

Negative checks: `unsupported_file.exe` → *".exe files are not accepted"* (blocked in the browser), `fake_renamed.pdf` → **415** *"The file content does not match a real .pdf file"* (blocked by the server).

## Step 14: Verify file storage

```powershell
Get-ChildItem -Recurse storage_data\assignments      # Windows
```
```bash
find storage_data/assignments -type f                 # macOS / Linux
```
Expected:
```
storage_data/assignments/assignment_006/student_008/20260925T103015Z_4be1c0a2.pdf
```

## Step 15: Verify submission metadata

```bash
python -c "import sqlite3; c=sqlite3.connect('portal.db'); [print(r) for r in c.execute('select submission_id, assignment_id, student_id, file_name, storage_path, submitted_at, submission_status, is_late from submissions order by submission_id desc limit 3')]"
```
Expected (first row):
```
(6, 6, 8, 'sample_assignment.pdf', 'assignments/assignment_006/student_008/20260925T103015Z_4be1c0a2.pdf', '2026-09-25 10:30:15.123456', 'SUBMITTED', 0)
```
The `storage_path` in the DB matches the file on disk. That is the link between database and object storage.

## Step 16: Teacher views the submission

Teacher → assignment → *Submissions* table → **Mark** → **Open file** (a signed URL opens the PDF in a new tab).

## Step 17: Teacher enters marks and feedback

Enter `17.5` and the feedback → **Save grade** → *Grade saved. The student can see it now.* The stamp changes to **GRADED**.
Try `25` on a 20-mark assignment: *"Marks must be between 0 and 20."* (browser) and **400 MARKS_EXCEED_MAXIMUM** (API).

## Step 18: Student views marks and feedback

Student → dashboard → **Recent feedback** shows the red-circled **17.5/20** and the comment. **My submissions** → **Feedback** shows the full view.

---

## Run the automated tests

```bash
pytest -v
```
Expected ending: `67 passed` (about 20–30 seconds).

## Late-submission demo (2 minutes)

Create an assignment with a deadline **2 minutes from now** and "Accept late work" ticked. Wait until it passes, then upload: the stamp says **LATE** and the message says *"It was recorded as LATE because the deadline had passed."* Untick "Accept late work" and upload again: **403** *"The deadline for this assignment has passed and late submissions are not accepted."*

---

## Path 2: mini-cloud with Docker (PostgreSQL + MinIO)

```bash
docker compose up --build            # starts db, storage, create-bucket, api
docker compose exec api python -m backend.seed
cd frontend && npm run dev
```
* API health: http://localhost:8000/api/health → `"dialect":"postgresql"`, `"provider":"s3"`
* MinIO console: http://localhost:9001 (user `portal-minio`, password `portal-minio-local-only`). Open bucket **assignment-submissions** → `assignments/…` to see uploaded objects.
* SQL: `docker compose exec db psql -U portal -d portal -c "select submission_id, storage_path, submission_status from submissions;"`

This is the same code talking to a real PostgreSQL server and a real S3 API. The only difference from production is the hostnames in the environment variables.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Frontend says *Cannot reach the server* | Backend not running, or `frontend/.env` `VITE_API_URL` wrong; restart `npm run dev` after editing `.env` |
| CORS error in browser console | Add your frontend origin to `CORS_ORIGINS` in `.env` and restart the API |
| Logged out after every API restart | You didn't set `SECRET_KEY`; a random dev key is generated each start |
| `ModuleNotFoundError: backend` | Run commands from the project root, not from inside `backend/` |
| Port already in use | `uvicorn … --port 8001` and update `VITE_API_URL` |
