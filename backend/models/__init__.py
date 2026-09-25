"""
ORM models. Importing this package registers every table on Base.metadata.

Relationships:
    User(teacher) 1 --- * Course 1 --- * Assignment 1 --- * Submission * --- 1 User(student)
    User(student) * --- * Course   (through Enrollment)
"""

from backend.models.assignment import Assignment
from backend.models.audit import AuditLog, RevokedToken
from backend.models.course import Course, Enrollment
from backend.models.enums import Role, SubmissionStatus
from backend.models.submission import Submission
from backend.models.user import User

__all__ = [
    "Assignment",
    "AuditLog",
    "Course",
    "Enrollment",
    "RevokedToken",
    "Role",
    "Submission",
    "SubmissionStatus",
    "User",
]
