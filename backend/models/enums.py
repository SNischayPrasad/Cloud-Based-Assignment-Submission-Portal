"""Enumerations used across the application."""

from enum import Enum


class Role(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class SubmissionStatus(str, Enum):
    # NOT_SUBMITTED is never stored - it is computed when a student has no
    # submission row for an assignment.
    NOT_SUBMITTED = "NOT_SUBMITTED"
    SUBMITTED = "SUBMITTED"
    LATE = "LATE"
    GRADED = "GRADED"
