from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class CourseCreate(BaseModel):
    course_code: str = Field(min_length=2, max_length=20, pattern=r"^[A-Za-z0-9\-]+$", examples=["CC401"])
    course_name: str = Field(min_length=3, max_length=150, examples=["Cloud Computing"])
    description: str = Field(default="", max_length=2000)
    teacher_id: int | None = Field(default=None, description="Admin only: owner teacher. Teachers always own their own courses.")

    @field_validator("course_code")
    @classmethod
    def upper_code(cls, value: str) -> str:
        return value.strip().upper()


class CourseOut(BaseModel):
    course_id: int
    course_code: str
    course_name: str
    description: str
    teacher_id: int
    teacher_name: str
    join_code: str | None = None  # only visible to the owning teacher / admin
    student_count: int
    assignment_count: int
    created_at: datetime


class JoinCourseRequest(BaseModel):
    join_code: str = Field(min_length=4, max_length=12)


class EnrollStudentRequest(BaseModel):
    email: EmailStr


class RosterStudent(BaseModel):
    student_id: int
    name: str
    email: str
    enrolled_at: datetime
