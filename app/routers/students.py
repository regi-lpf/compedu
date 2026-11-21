import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.audit import audit
from app.deps import CurrentUser, Db, EnrollmentManager, forbidden, not_found
from app.models import Enrollment, SchoolClass, Student
from app.policies import active_year, can_view_student, scope_students
from app.schemas import EnrollmentCreate, StudentCreate, StudentDetail, StudentRead, StudentUpdate
from app.serializers import student_detail, student_read

router = APIRouter(prefix="/students", tags=["alunos"])

_LOAD = selectinload(Student.enrollments).selectinload(Enrollment.school_class).selectinload(SchoolClass.academic_year)


def _load(db: Db, student_id: uuid.UUID) -> Student:
    student = db.scalar(select(Student).options(_LOAD).where(Student.id == student_id).execution_options(populate_existing=True))
    if not student:
        raise not_found("Aluno")
    return student


def _year_id(db: Db):
    year = active_year(db)
    return year.id if year else None


def _enroll(db: Db, student: Student, class_id: uuid.UUID) -> Enrollment:
    """Matricula o aluno na turma. Se já houver vínculo vigente no mesmo ano, encerra-o (troca de turma)."""
    school_class = db.get(SchoolClass, class_id)
    if not school_class:
        raise not_found("Turma")
    current = db.scalar(select(Enrollment).where(Enrollment.student_id == student.id, Enrollment.ended_at.is_(None),
                                                 Enrollment.academic_year_id == school_class.academic_year_id))
    if current is not None:
        if current.class_id == class_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "O aluno já está matriculado nesta turma")
        current.ended_at = date.today()
        db.flush()  # libera o índice único de vínculo vigente antes de inserir o novo
    enrollment = Enrollment(student_id=student.id, class_id=class_id,
                            academic_year_id=school_class.academic_year_id, started_at=date.today())
    db.add(enrollment)
    db.flush()
    return enrollment


@router.get("", response_model=list[StudentRead])
def list_students(db: Db, user: CurrentUser, class_id: uuid.UUID | None = None,
                  q: str | None = Query(default=None, max_length=80)):
    stmt = scope_students(select(Student).options(_LOAD), user)
    if class_id is not None:
        stmt = stmt.where(Student.id.in_(select(Enrollment.student_id).where(
            Enrollment.class_id == class_id, Enrollment.ended_at.is_(None))))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Student.full_name.ilike(like), Student.school_identifier.ilike(like)))
    year_id = _year_id(db)
    return [student_read(s, year_id) for s in db.scalars(stmt.order_by(Student.full_name)).all()]


@router.post("", response_model=StudentDetail, status_code=201)
def create_student(payload: StudentCreate, db: Db, user: EnrollmentManager):
    """Cria o cadastro do aluno e, se informada a turma, já cria o vínculo (fluxo de 'aluno novo')."""
    if db.scalar(select(Student.id).where(Student.school_identifier == payload.school_identifier)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um aluno com esse identificador escolar")
    student = Student(full_name=payload.full_name, school_identifier=payload.school_identifier)
    db.add(student)
    db.flush()
    if payload.class_id:
        _enroll(db, student, payload.class_id)
    audit(db, user, "create", "student", student.id)
    db.commit()
    return student_detail(_load(db, student.id), _year_id(db))


@router.get("/{student_id}", response_model=StudentDetail)
def get_student(student_id: uuid.UUID, db: Db, user: CurrentUser):
    if not can_view_student(db, user, student_id):
        raise not_found("Aluno")
    return student_detail(_load(db, student_id), _year_id(db))


@router.patch("/{student_id}", response_model=StudentDetail)
def update_student(student_id: uuid.UUID, payload: StudentUpdate, db: Db, user: EnrollmentManager):
    student = _load(db, student_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("school_identifier") and data["school_identifier"] != student.school_identifier and db.scalar(
            select(Student.id).where(Student.school_identifier == data["school_identifier"])):
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um aluno com esse identificador escolar")
    for key, value in data.items():
        setattr(student, key, value)
    audit(db, user, "update", "student", student.id, ",".join(sorted(data)))
    db.commit()
    return student_detail(_load(db, student.id), _year_id(db))


@router.post("/{student_id}/enrollments", response_model=StudentDetail, status_code=201)
def enroll_student(student_id: uuid.UUID, payload: EnrollmentCreate, db: Db, user: EnrollmentManager):
    """Vincula um aluno existente a uma turma ou o transfere de turma, preservando o histórico."""
    student = _load(db, student_id)
    if not student.active:
        raise forbidden("Aluno inativo")
    enrollment = _enroll(db, student, payload.class_id)
    audit(db, user, "enroll", "student", student.id, f"class={enrollment.class_id}")
    db.commit()
    return student_detail(_load(db, student.id), _year_id(db))
