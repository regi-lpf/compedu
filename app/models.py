import uuid
from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    CheckConstraint, Date, DateTime, Enum as SqlEnum, ForeignKey, Index, String, Text, UniqueConstraint, Uuid, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(str, Enum):
    admin = "admin"
    coordination = "coordination"
    teacher = "teacher"
    secretary = "secretary"
    support = "support"


DEFAULT_LEVEL: dict[Role, int] = {
    Role.admin: 1, Role.coordination: 2, Role.teacher: 3, Role.secretary: 4, Role.support: 5,
}


class RecordType(str, Enum):
    positive = "positive"
    attention = "attention"
    follow_up = "follow_up"


def _enum(enum_cls, name: str):
    # VARCHAR + CHECK: portável entre SQLite e PostgreSQL e simples de migrar.
    return SqlEnum(enum_cls, name=name, native_enum=False, length=20, validate_strings=True)


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("access_level BETWEEN 1 AND 5", name="ck_user_access_level"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[Role] = mapped_column(_enum(Role, "user_role"))
    access_level: Mapped[int] = mapped_column(default=3)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assignments: Mapped[list["TeachingAssignment"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def verify_access(self, target_level: int) -> bool:
        """Regra vertical: o usuário de nível U lê conteúdos de nível P quando P >= U."""
        return target_level >= self.access_level


class AcademicYear(Base):
    __tablename__ = "academic_years"

    id: Mapped[uuid.UUID] = _uuid_pk()
    year_label: Mapped[str] = mapped_column(String(20), unique=True)
    is_active: Mapped[bool] = mapped_column(default=False)
    council_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    classes: Mapped[list["SchoolClass"]] = relationship(back_populates="academic_year")


class SchoolClass(Base):
    __tablename__ = "school_classes"
    __table_args__ = (UniqueConstraint("academic_year_id", "name", name="uq_class_name_per_year"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(80))
    grade_level: Mapped[str] = mapped_column(String(80))
    academic_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_years.id", ondelete="RESTRICT"), index=True)

    academic_year: Mapped[AcademicYear] = relationship(back_populates="classes")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="school_class")
    assignments: Mapped[list["TeachingAssignment"]] = relationship(back_populates="school_class", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = _uuid_pk()
    full_name: Mapped[str] = mapped_column(String(160), index=True)
    school_identifier: Mapped[str] = mapped_column(String(40), unique=True)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student", order_by="Enrollment.started_at")


class Enrollment(Base):
    """Vínculo aluno–turma dentro de um ano letivo. Trocar de turma encerra o vínculo vigente (ended_at)."""
    __tablename__ = "enrollments"
    __table_args__ = (
        Index("uq_current_enrollment_per_year", "student_id", "academic_year_id", unique=True,
              sqlite_where=text("ended_at IS NULL"), postgresql_where=text("ended_at IS NULL")),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"), index=True)
    class_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("school_classes.id", ondelete="RESTRICT"), index=True)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_years.id", ondelete="RESTRICT"), index=True)
    started_at: Mapped[date] = mapped_column(Date, default=date.today)
    ended_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    student: Mapped[Student] = relationship(back_populates="enrollments")
    school_class: Mapped[SchoolClass] = relationship(back_populates="enrollments")


class TeachingAssignment(Base):
    """Vínculo profissional–turma. O ano letivo vem da própria turma."""
    __tablename__ = "teaching_assignments"
    __table_args__ = (UniqueConstraint("user_id", "class_id", name="uq_assignment"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    class_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("school_classes.id", ondelete="CASCADE"), index=True)

    user: Mapped[User] = relationship(back_populates="assignments")
    school_class: Mapped[SchoolClass] = relationship(back_populates="assignments")


class PedagogicalRecord(Base):
    __tablename__ = "pedagogical_records"
    __table_args__ = (CheckConstraint("access_level BETWEEN 1 AND 5", name="ck_record_access_level"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    record_type: Mapped[RecordType] = mapped_column(_enum(RecordType, "record_type"))
    access_level: Mapped[int] = mapped_column(default=3)
    text_content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"), index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    class_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("school_classes.id", ondelete="RESTRICT"), index=True)

    student: Mapped[Student] = relationship()
    author: Mapped[User] = relationship()
    school_class: Mapped[SchoolClass] = relationship()


class Announcement(Base):
    __tablename__ = "announcements"
    __table_args__ = (CheckConstraint("access_level BETWEEN 1 AND 5", name="ck_announcement_access_level"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    title: Mapped[str] = mapped_column(String(180))
    content: Mapped[str] = mapped_column(Text)
    access_level: Mapped[int] = mapped_column(default=3)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)

    author: Mapped[User] = relationship()


class AuditLog(Base):
    """Trilha de auditoria: registra quem fez o quê, sem copiar o conteúdo pedagógico."""
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(40))
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    actor: Mapped[User | None] = relationship()
