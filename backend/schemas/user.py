from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.schemas.validation import validate_password_strength


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime


class AdminCreateUser(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: Literal["student", "teacher", "admin"]

    _check_password = field_validator("password")(validate_password_strength)


class AdminUpdateUser(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    role: Literal["student", "teacher", "admin"] | None = None
    is_active: bool | None = None


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_id: int
    user_id: int | None
    action: str
    entity_type: str | None
    entity_id: int | None
    details: str | None
    ip_address: str | None
    created_at: datetime
