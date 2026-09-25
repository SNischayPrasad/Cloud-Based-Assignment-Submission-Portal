from pydantic import BaseModel, EmailStr, Field, field_validator

from backend.schemas.user import UserOut
from backend.schemas.validation import clean_text, validate_password_strength


class RegisterRequest(BaseModel):
    """Public self-registration always creates a STUDENT account.
    Teacher/admin accounts are created by an admin (no role escalation)."""

    name: str = Field(min_length=2, max_length=120, examples=["Aarav Sharma"])
    email: EmailStr = Field(examples=["aarav.student@portal.dev"])
    password: str = Field(min_length=8, max_length=72, examples=["Student@123"])

    _clean_name = field_validator("name")(clean_text)
    _check_password = field_validator("password")(validate_password_strength)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class MessageResponse(BaseModel):
    message: str
