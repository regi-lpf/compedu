from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models import RecordType, Role


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: Role
    access_level: int = Field(default=3, ge=1, le=5)
    class_ids: list[int] = Field(default_factory=list)


class UserRead(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: Role
    access_level: int
    class_ids: list[int]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    year: str = Field(min_length=1, max_length=40)


class ClassRead(BaseModel):
    id: int
    name: str
    year: str
    student_count: int


class StudentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    class_id: int


class StudentRead(BaseModel):
    id: int
    name: str
    class_id: int
    class_name: str


class RecordCreate(BaseModel):
    student_id: int
    kind: RecordType
    access_level: int = Field(ge=1, le=5)
    body: str = Field(min_length=1, max_length=10000)


class RecordRead(BaseModel):
    id: int
    student_id: int
    student_name: str
    class_id: int
    class_name: str
    author_name: str
    kind: RecordType
    access_level: int
    body: str
    created_at: datetime


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    body: str = Field(min_length=1, max_length=10000)
    access_level: int = Field(ge=1, le=5)


class AnnouncementRead(BaseModel):
    id: int
    title: str
    body: str
    access_level: int
    author_name: str
    created_at: datetime
