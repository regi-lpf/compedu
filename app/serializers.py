"""Conversão de entidades ORM para os contratos da API."""
from app.models import Announcement, Enrollment, PedagogicalRecord, Student, User
from app.schemas import (
    AnnouncementRead, ClassRef, EnrollmentRead, RecordRead, StudentDetail, StudentRead, UserRead,
)


def record_read(r: PedagogicalRecord) -> RecordRead:
    return RecordRead(
        id=r.id, student_id=r.student_id, student_name=r.student.full_name, class_id=r.class_id,
        class_name=r.school_class.name, author_id=r.author_id, author_name=r.author.name,
        record_type=r.record_type, access_level=r.access_level, text_content=r.text_content,
        created_at=r.created_at, updated_at=r.updated_at,
    )


def announcement_read(a: Announcement) -> AnnouncementRead:
    return AnnouncementRead(id=a.id, title=a.title, content=a.content, access_level=a.access_level,
                            author_id=a.author_id, author_name=a.author.name, published_at=a.published_at,
                            updated_at=a.updated_at)


def user_classes(user: User, year_id) -> list[ClassRef]:
    if year_id is None:
        return []
    classes = [a.school_class for a in user.assignments if a.school_class.academic_year_id == year_id]
    return [ClassRef(id=c.id, name=c.name) for c in sorted(classes, key=lambda c: c.name)]


def user_read(user: User, year_id) -> UserRead:
    return UserRead(id=user.id, name=user.name, email=user.email, role=user.role, access_level=user.access_level,
                    active=user.active, classes=user_classes(user, year_id))


def current_enrollment(student: Student, year_id) -> Enrollment | None:
    if year_id is None:
        return None
    return next((e for e in student.enrollments if e.academic_year_id == year_id and e.ended_at is None), None)


def student_read(student: Student, year_id) -> StudentRead:
    cur = current_enrollment(student, year_id)
    return StudentRead(id=student.id, full_name=student.full_name, school_identifier=student.school_identifier,
                       active=student.active, current_class_id=cur.class_id if cur else None,
                       current_class_name=cur.school_class.name if cur else None)


def student_detail(student: Student, year_id) -> StudentDetail:
    base = student_read(student, year_id)
    enrollments = [EnrollmentRead(id=e.id, class_id=e.class_id, class_name=e.school_class.name,
                                  year_label=e.school_class.academic_year.year_label,
                                  started_at=e.started_at, ended_at=e.ended_at)
                   for e in student.enrollments]
    return StudentDetail(**base.model_dump(), enrollments=enrollments)
