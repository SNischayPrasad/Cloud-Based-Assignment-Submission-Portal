"""
Seed the database with DUMMY demo data (fictional people and courses).

    python -m backend.seed            # add demo data if the DB is empty
    python -m backend.seed --reset    # drop everything and re-create

The demo password is read from SEED_DEMO_PASSWORD (see .env.example).
If it is not set, a random password is generated and printed once.
"""

import argparse
import os
import secrets
import sys
from datetime import timedelta

from sqlalchemy import func, select

from backend.config import get_settings
from backend.models import Assignment, Course, Enrollment, Role, Submission, SubmissionStatus, User
from backend.utils import time_utils
from backend.utils.logging_config import configure_logging
from backend.utils.pdf_builder import build_pdf
from cloud.auth_service import hash_password
from cloud.database_service import drop_all, get_session_factory, init_db
from cloud.storage_service import get_storage_service

USERS = [
    ("Portal Admin", "admin@portal.dev", Role.ADMIN),
    ("Dr. Meera Iyer", "meera.iyer@portal.dev", Role.TEACHER),
    ("Prof. Daniel Brooks", "daniel.brooks@portal.dev", Role.TEACHER),
    ("Aarav Sharma", "aarav@portal.dev", Role.STUDENT),
    ("Priya Nair", "priya@portal.dev", Role.STUDENT),
    ("Rahul Verma", "rahul@portal.dev", Role.STUDENT),
    ("Sara Khan", "sara@portal.dev", Role.STUDENT),
]

COURSES = [
    ("CC401", "Cloud Computing", "IaaS, PaaS, SaaS, virtualization, object storage and serverless.", "meera.iyer@portal.dev", "CLOUD4"),
    ("DB302", "Database Systems", "Relational modelling, SQL, normalization and indexing.", "daniel.brooks@portal.dev", "DBSYS3"),
]

ENROLLMENTS = {
    "CC401": ["aarav@portal.dev", "priya@portal.dev", "rahul@portal.dev", "sara@portal.dev"],
    "DB302": ["aarav@portal.dev", "priya@portal.dev", "rahul@portal.dev"],
}

# (course, title, description, days_from_now, max_marks, file types, max MB, allow late, allow resubmit)
ASSIGNMENTS = [
    ("CC401", "Design a Three-Tier Cloud Architecture",
     "Draw and explain a three-tier web architecture on a public cloud. Cover the load balancer, "
     "autoscaling group, managed database and object storage. Submit a PDF report (max 6 pages).",
     7, 20, "pdf,docx", 10, True, True),
    ("CC401", "Object Storage Lab: Lifecycle Policies",
     "Create a private bucket, upload three objects, generate a pre-signed URL and configure a lifecycle "
     "rule. Submit screenshots and a short write-up as a PDF or ZIP.",
     3, 10, "pdf,zip", 10, True, True),
    ("CC401", "Virtualization vs Containers Report",
     "Compare hypervisor-based virtualization with containers. Include a table of trade-offs.",
     -2, 10, "pdf", 5, True, True),
    ("DB302", "ER Diagram for a Hospital System",
     "Model patients, doctors, appointments and prescriptions. Submit the ER diagram as PDF or PNG.",
     5, 15, "pdf,png", 5, False, True),
    ("DB302", "SQL Normalization Worksheet",
     "Normalize the given relation to 3NF and justify each step.",
     -1, 10, "pdf", 5, False, False),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo data")
    parser.add_argument("--reset", action="store_true", help="drop all tables before seeding")
    args = parser.parse_args()

    settings = get_settings()
    configure_logging("WARNING")
    if args.reset:
        if settings.environment == "production":
            sys.exit("Refusing to --reset in production.")
        drop_all()
    init_db()

    session = get_session_factory()()
    if session.scalar(select(func.count(User.user_id))) > 0:
        print("Database already has users - nothing seeded. Use --reset to start over.")
        return

    password = os.getenv("SEED_DEMO_PASSWORD") or ("Demo-" + secrets.token_urlsafe(9))
    password_hash = hash_password(password)
    now = time_utils.utcnow()
    storage = get_storage_service()

    users = {email: User(name=name, email=email, role=role.value, password_hash=password_hash) for name, email, role in USERS}
    session.add_all(users.values())
    session.flush()

    courses = {}
    for code, name, description, teacher_email, join_code in COURSES:
        courses[code] = Course(course_code=code, course_name=name, description=description,
                               teacher_id=users[teacher_email].user_id, join_code=join_code)
    session.add_all(courses.values())
    session.flush()

    for code, emails in ENROLLMENTS.items():
        for email in emails:
            session.add(Enrollment(course_id=courses[code].course_id, student_id=users[email].user_id))

    assignments = {}
    for code, title, description, days, marks, types, max_mb, late, resubmit in ASSIGNMENTS:
        course = courses[code]
        assignment = Assignment(
            course_id=course.course_id, title=title, description=description,
            deadline=(now + timedelta(days=days)).replace(hour=18, minute=30, second=0, microsecond=0),
            max_marks=marks, allowed_file_types=types, max_file_size_mb=max_mb,
            allow_late_submission=late, allow_resubmission=resubmit, created_by=course.teacher_id,
        )
        session.add(assignment)
        assignments[title] = assignment
    session.flush()

    def add_submission(email, title, hours_after_deadline, marks=None, feedback=None):
        student, assignment = users[email], assignments[title]
        submitted_at = assignment.deadline + timedelta(hours=hours_after_deadline)
        data = build_pdf([f"{assignment.title}", f"Submitted by {student.name}", "Demo submission generated by seed script."])
        path = (f"assignments/assignment_{assignment.assignment_id:03d}/student_{student.user_id:03d}/"
                f"{time_utils.storage_timestamp(submitted_at)}_{secrets.token_hex(4)}.pdf")
        stored = storage.upload(path, data, "application/pdf")
        is_late = submitted_at > assignment.deadline
        status = SubmissionStatus.LATE.value if is_late else SubmissionStatus.SUBMITTED.value
        submission = Submission(
            assignment_id=assignment.assignment_id, student_id=student.user_id,
            file_name=f"{student.name.split()[0].lower()}_{assignment.assignment_id}.pdf",
            file_url=stored.uri, storage_path=stored.path, file_size=stored.size, content_type="application/pdf",
            checksum_sha256=stored.checksum_sha256, submitted_at=submitted_at, submission_status=status,
            is_late=is_late, attempt_number=1,
        )
        if marks is not None:
            submission.marks, submission.feedback = marks, feedback
            submission.graded_at = min(submitted_at + timedelta(days=1), now)
            submission.graded_by = assignment.created_by
            submission.submission_status = SubmissionStatus.GRADED.value
        session.add(submission)

    add_submission("priya@portal.dev", "Virtualization vs Containers Report", -30, 9,
                   "Clear comparison table and good use of real examples (KVM vs Docker). "
                   "Add a sentence on cold-start latency for containers vs VMs.")
    add_submission("aarav@portal.dev", "Virtualization vs Containers Report", 5, 6.5,
                   "Submitted 5 hours late. Content is correct but the trade-off table is missing "
                   "security isolation. Please cite your sources.")
    add_submission("rahul@portal.dev", "Virtualization vs Containers Report", -3)
    add_submission("priya@portal.dev", "SQL Normalization Worksheet", -12, 8.5,
                   "Correct 2NF and 3NF decomposition. Explain the functional dependency B -> C more carefully.")

    session.commit()
    session.close()

    print("\nDemo data created (all names and emails are fictional).\n")
    print(f"{'Role':<9}{'Email':<28}Name")
    for name, email, role in USERS:
        print(f"{role.value:<9}{email:<28}{name}")
    print(f"\nPassword for every demo account: {password}")
    if not os.getenv("SEED_DEMO_PASSWORD"):
        print("(randomly generated - set SEED_DEMO_PASSWORD in .env to choose your own)")
    print("Course join codes: CC401 -> CLOUD4, DB302 -> DBSYS3\n")


if __name__ == "__main__":
    main()
