import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import RecordType, Role


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Autenticação ----------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=10)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthConfig(BaseModel):
    google_client_id: str
    dev_login_enabled: bool
    allowed_domain: str


class ClassRef(ORM):
    id: uuid.UUID
    name: str


class Me(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    role: Role
    access_level: int
    classes: list[ClassRef]
    active_year: str | None


# ---------- Usuários ----------
class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    role: Role
    access_level: int | None = Field(default=None, ge=1, le=5)
    password: str | None = Field(default=None, min_length=12, max_length=128)
    class_ids: list[uuid.UUID] = Field(default_factory=list)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    role: Role | None = None
    access_level: int | None = Field(default=None, ge=1, le=5)
    active: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=128)


class AssignmentsUpdate(BaseModel):
    class_ids: list[uuid.UUID]


class UserRead(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    role: Role
    access_level: int
    active: bool
    classes: list[ClassRef]


# ---------- Ano letivo / turmas ----------
class AcademicYearCreate(BaseModel):
    year_label: str = Field(min_length=4, max_length=20)
    is_active: bool = False


class AcademicYearUpdate(BaseModel):
    year_label: str | None = Field(default=None, min_length=4, max_length=20)
    is_active: bool | None = None
    council_date: date | None = None


class AcademicYearRead(ORM):
    id: uuid.UUID
    year_label: str
    is_active: bool
    council_date: date | None


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    grade_level: str = Field(min_length=1, max_length=80)
    academic_year_id: uuid.UUID | None = None  # padrão: ano ativo


class ClassUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    grade_level: str | None = Field(default=None, min_length=1, max_length=80)


class ClassRead(BaseModel):
    id: uuid.UUID
    name: str
    grade_level: str
    academic_year_id: uuid.UUID
    year_label: str
    student_count: int
    record_count: int | None = None


class ClassReport(BaseModel):
    class_id: uuid.UUID
    class_name: str
    year_label: str
    student_count: int
    total: int
    by_type: dict[RecordType, int]


# ---------- Alunos / matrículas ----------
class StudentCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    school_identifier: str = Field(min_length=1, max_length=40)
    class_id: uuid.UUID | None = None

    @field_validator("full_name", "school_identifier")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class StudentUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    school_identifier: str | None = Field(default=None, min_length=1, max_length=40)
    active: bool | None = None


class EnrollmentCreate(BaseModel):
    class_id: uuid.UUID


class EnrollmentRead(BaseModel):
    id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    year_label: str
    started_at: date
    ended_at: date | None


class StudentRead(BaseModel):
    id: uuid.UUID
    full_name: str
    school_identifier: str
    active: bool
    current_class_id: uuid.UUID | None
    current_class_name: str | None


class StudentDetail(StudentRead):
    enrollments: list[EnrollmentRead]


class StudentImportRowRead(BaseModel):
    line_number: int
    full_name: str | None
    status: Literal[
        "new", "needs_confirmation", "already_enrolled", "ambiguous", "duplicate", "invalid", "inactive",
    ]
    student_id: uuid.UUID | None = None
    current_class_id: uuid.UUID | None = None
    current_class_name: str | None = None
    message: str | None = None


class StudentImportPreview(BaseModel):
    class_id: uuid.UUID
    class_name: str
    rows: list[StudentImportRowRead]
    new_count: int
    confirmation_count: int
    ignored_count: int
    duplicate_count: int


class StudentImportResult(BaseModel):
    created_count: int
    enrolled_count: int
    transferred_count: int
    ignored_count: int
    duplicate_count: int


# ---------- Registros pedagógicos ----------
class RecordCreate(BaseModel):
    student_id: uuid.UUID
    record_type: RecordType
    access_level: int = Field(default=3, ge=1, le=5)
    text_content: str = Field(min_length=1, max_length=10000)


class RecordUpdate(BaseModel):
    record_type: RecordType | None = None
    access_level: int | None = Field(default=None, ge=1, le=5)
    text_content: str | None = Field(default=None, min_length=1, max_length=10000)


class RecordRead(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    class_id: uuid.UUID
    class_name: str
    author_id: uuid.UUID
    author_name: str
    record_type: RecordType
    access_level: int
    text_content: str
    created_at: datetime
    updated_at: datetime | None


# ---------- Mural ----------
class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1, max_length=10000)
    access_level: int = Field(default=3, ge=1, le=5)


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    content: str | None = Field(default=None, min_length=1, max_length=10000)
    access_level: int | None = Field(default=None, ge=1, le=5)


class AnnouncementRead(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    access_level: int
    author_id: uuid.UUID
    author_name: str
    published_at: datetime
    updated_at: datetime | None


# ---------- Painel / auditoria ----------
class WatchItem(BaseModel):
    student_id: uuid.UUID
    student_name: str
    class_name: str | None
    attention_count: int


class Dashboard(BaseModel):
    student_count: int
    class_count: int
    records_this_month: int
    council_date: date | None
    active_year: str | None
    recent_records: list[RecordRead]
    watch_students: list[WatchItem]


class AuditRead(BaseModel):
    id: uuid.UUID
    actor_name: str | None
    action: str
    entity: str
    entity_id: str | None
    detail: str | None
    created_at: datetime
