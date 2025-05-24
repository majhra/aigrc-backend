from datetime import datetime
from typing import Annotated, Literal
import uuid

from fastapi import Form
from pydantic import BaseModel, EmailStr, field_validator, UUID4
from pydantic.dataclasses import dataclass

from app.api import utils


class Token(BaseModel):
    access_token: str
    token_type: str


class Group(BaseModel):
    id: UUID4
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime
    status: Literal["ACTIVE", "INACTIVE", "SUSPENDED"] = "ACTIVE"
    settings: dict | None = None

    @field_validator("id", mode="before")
    def set_id(cls, v):
        if v is None:
            return uuid.uuid4()
        return v

    @field_validator("name")
    def validate_name(cls, name):
        if not name or len(name.strip()) == 0:
            raise ValueError("Group name cannot be empty")
        return name.strip()


class GroupCreate(BaseModel):
    name: str
    description: str | None = None
    settings: dict | None = None


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: Literal["ACTIVE", "INACTIVE", "SUSPENDED"] | None = None
    settings: dict | None = None


class GroupResponse(BaseModel):
    id: UUID4
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime
    status: Literal["ACTIVE", "INACTIVE", "SUSPENDED"]
    settings: dict | None = None


class UserResponse(BaseModel):
    id: UUID4
    email: str
    full_name: str | None = None
    created_at: datetime
    is_verified: bool
    disabled: bool
    group: GroupResponse | None = None

    @field_validator("email", mode="before")
    def lowercase_and_strip_email(cls, email, **kwargs):
        return utils.format_email(email)


class RegistrationUserRepsonse(BaseModel):
    message: str
    data: UserResponse


class TokenData(BaseModel):
    email: str | None = None


class User(BaseModel):
    id: UUID4 | None = None
    email: str | None = None
    full_name: str | None = None
    password: str | None = None
    disabled: bool | None = None
    created_at: datetime | None = None
    last_login: datetime | None = None
    is_verified: bool | None = None
    verification_code: str | None = None
    verification_code_expires_at: datetime | None = None
    password_reset_code: str | None = None
    password_reset_code_expires_at: datetime | None = None
    role: str | None = None
    group: str | None = None

    @field_validator("id", mode="before")
    def set_id(cls, v):
        if v is None:
            return uuid.uuid4()
        return v

    @field_validator("email", mode="before")
    def lowercase_and_strip_email(cls, email, **kwargs):
        if email is None:
            return None
        return utils.format_email(email)


class UserInDB(User):
    password: str


class EmailVerification(BaseModel):
    email: str
    verification_code: str


class SupportRequest(BaseModel):
    message: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    group_id: UUID4 | None = None
    password: str | None = None

    @field_validator("password")
    def validate_password(cls, password, **kwargs):
        if password is not None:
            return utils.validate_password(password)
        return password


class UserPasswordResetRequest(BaseModel):
    email: EmailStr


@dataclass
class UserSignup:
    email: Annotated[EmailStr, Form()]
    password: Annotated[str, Form()]

    @field_validator("email", mode="before")
    def lowercase_and_strip_email(cls, email, **kwargs):
        return utils.format_email(email)

    @field_validator("password")
    def validate_password(cls, password, **kwargs):
        return utils.validate_password(password)


@dataclass
class UserEmailVerification:
    email: Annotated[EmailStr, Form()]
    verification_code: Annotated[str, Form()]

    @field_validator("email", mode="before")
    def lowercase_and_strip_email(cls, email, **kwargs):
        return utils.format_email(email)

    @field_validator("verification_code", mode="before")
    def validate_password_reset_code(cls, password_reset_code, **kwargs):
        return password_reset_code.upper().strip()


@dataclass
class UserPasswordResetVerify:
    email: Annotated[EmailStr, Form()]
    new_password: Annotated[str, Form()]
    password_reset_code: Annotated[str, Form()]

    @field_validator("email", mode="before")
    def lowercase_and_strip_email(cls, email, **kwargs):
        return utils.format_email(email)

    @field_validator("new_password")
    def validate_password(cls, password, **kwargs):
        return utils.validate_password(password)

    @field_validator("password_reset_code", mode="before")
    def validate_password_reset_code(cls, password_reset_code, **kwargs):
        return password_reset_code.upper().strip()
