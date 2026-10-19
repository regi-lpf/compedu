from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, Column, DateTime, Enum as SqlEnum, ForeignKey, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(str, Enum):
    admin = "admin"
    teacher = "teacher"
    coordination = "coordination"
    secretary = "secretary"
    support = "support"


class RecordType(str, Enum):
    positive = "positive"
    attention = "attention"
    follow_up = "follow_up"


teacher_classes = Table(
    "teacher_classes",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("class_id", ForeignKey("school_classes.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("access_level BETWEEN 1 AND 5", name="ck_user_access_level"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(SqlEnum(Role, name="user_role"))
    access_level: Mapped[int] = mapped_column(default=3)
    active: Mapped[bool] = mapped_column(default=True)
    classes: Mapped[list["SchoolClass"]] = relationship(secondary=teacher_classes, back_populates="teachers")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SchoolClass(Base):
    __tablename__ = "school_classes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    year: Mapped[str] = mapped_column(String(40))
    students: Mapped[list["Student"]] = relationship(back_populates="school_class", cascade="all, delete-orphan")
    teachers: Mapped[list[User]] = relationship(secondary=teacher_classes, back_populates="classes")


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    class_id: Mapped[int] = mapped_column(ForeignKey("school_classes.id", ondelete="CASCADE"), index=True)
    school_class: Mapped[SchoolClass] = relationship(back_populates="students")
    records: Mapped[list["PedagogicalRecord"]] = relationship(back_populates="student", cascade="all, delete-orphan")


class PedagogicalRecord(Base):
    __tablename__ = "pedagogical_records"
    __table_args__ = (CheckConstraint("access_level BETWEEN 1 AND 5", name="ck_record_access_level"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[RecordType] = mapped_column(SqlEnum(RecordType, name="record_type"))
    access_level: Mapped[int] = mapped_column(default=3)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    student: Mapped[Student] = relationship(back_populates="records")
    author: Mapped[User] = relationship()


class Announcement(Base):
    __tablename__ = "announcements"
    __table_args__ = (CheckConstraint("access_level BETWEEN 1 AND 5", name="ck_announcement_access_level"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    access_level: Mapped[int] = mapped_column(default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    author: Mapped[User] = relationship()
