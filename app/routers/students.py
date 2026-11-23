import uuid
from datetime import date

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.audit import audit
from app.deps import CurrentUser, Db, EnrollmentManager, forbidden, not_found
from app.models import AcademicYear, Enrollment, SchoolClass, Student
from app.policies import active_year, can_view_student, scope_students
from app.schemas import (
    EnrollmentCreate, StudentCreate, StudentDetail, StudentImportPreview, StudentImportResult, StudentImportRowRead,
    StudentRead, StudentUpdate,
)
from app.serializers import student_detail, student_read
from app.student_imports import (
    MAX_IMPORT_BYTES, StudentImportRow, generated_school_identifier, normalize_student_name, parse_student_import,
)

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


async def _uploaded_rows(file: UploadFile) -> list[StudentImportRow]:
    if not file.filename:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "O arquivo enviado não tem nome.")
    content = await file.read(MAX_IMPORT_BYTES + 1)
    try:
        return parse_student_import(file.filename, content)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


def _import_target(db: Db, class_id: uuid.UUID) -> SchoolClass:
    target = db.scalar(
        select(SchoolClass).join(AcademicYear).where(
            SchoolClass.id == class_id, AcademicYear.is_active.is_(True)
        )
    )
    if not target:
        raise not_found("Turma do ano letivo ativo")
    return target


def _build_import_preview(
    db: Db, rows: list[StudentImportRow], target: SchoolClass,
) -> StudentImportPreview:
    existing_rows = db.execute(
        select(Student.id, Student.full_name, Student.active, Enrollment.class_id, SchoolClass.name)
        .outerjoin(Enrollment, and_(
            Enrollment.student_id == Student.id,
            Enrollment.academic_year_id == target.academic_year_id,
            Enrollment.ended_at.is_(None),
        ))
        .outerjoin(SchoolClass, SchoolClass.id == Enrollment.class_id)
    ).all()
    existing_by_name: dict[str, list[tuple[uuid.UUID, str, bool, uuid.UUID | None, str | None]]] = {}
    for student_id, full_name, active, class_id, class_name in existing_rows:
        existing_by_name.setdefault(normalize_student_name(full_name), []).append(
            (student_id, full_name, active, class_id, class_name)
        )

    result: list[StudentImportRowRead] = []
    seen_names: set[str] = set()
    new_count = confirmation_count = ignored_count = duplicate_count = 0
    for row in rows:
        if row.full_name is None:
            result.append(StudentImportRowRead(
                line_number=row.line_number, full_name=None, status="invalid",
                message="Linha sem um nome válido de aluno.",
            ))
            ignored_count += 1
            continue
        normalized = normalize_student_name(row.full_name)
        if normalized in seen_names:
            result.append(StudentImportRowRead(
                line_number=row.line_number, full_name=row.full_name, status="duplicate",
                message="Nome repetido nesta planilha; esta linha será ignorada.",
            ))
            duplicate_count += 1
            continue
        seen_names.add(normalized)
        matches = existing_by_name.get(normalized, [])
        if len(matches) > 1:
            result.append(StudentImportRowRead(
                line_number=row.line_number, full_name=row.full_name, status="ambiguous",
                message="Há mais de um aluno cadastrado com este nome; revise manualmente.",
            ))
            ignored_count += 1
        elif matches:
            student_id, _full_name, active, current_class_id, current_class_name = matches[0]
            if not active:
                result.append(StudentImportRowRead(
                    line_number=row.line_number, full_name=row.full_name, status="inactive",
                    student_id=student_id, current_class_id=current_class_id, current_class_name=current_class_name,
                    message="O aluno correspondente está inativo e não será matriculado.",
                ))
                ignored_count += 1
            elif current_class_id == target.id:
                result.append(StudentImportRowRead(
                    line_number=row.line_number, full_name=row.full_name, status="already_enrolled",
                    student_id=student_id, current_class_id=current_class_id, current_class_name=current_class_name,
                    message="O aluno já está matriculado nesta turma.",
                ))
                ignored_count += 1
            else:
                result.append(StudentImportRowRead(
                    line_number=row.line_number, full_name=row.full_name, status="needs_confirmation",
                    student_id=student_id, current_class_id=current_class_id, current_class_name=current_class_name,
                    message="Confirme para matricular este aluno existente.",
                ))
                confirmation_count += 1
        else:
            result.append(StudentImportRowRead(
                line_number=row.line_number, full_name=row.full_name, status="new",
            ))
            new_count += 1

    return StudentImportPreview(
        class_id=target.id, class_name=target.name, rows=result, new_count=new_count,
        confirmation_count=confirmation_count, ignored_count=ignored_count, duplicate_count=duplicate_count,
    )


@router.post("/import/preview", response_model=StudentImportPreview)
async def preview_student_import(
    db: Db,
    _user: EnrollmentManager,
    class_id: uuid.UUID = Form(),
    file: UploadFile = File(),
):
    rows = await _uploaded_rows(file)
    target = _import_target(db, class_id)
    return _build_import_preview(db, rows, target)


@router.post("/import/confirm", response_model=StudentImportResult)
async def confirm_student_import(
    db: Db,
    user: EnrollmentManager,
    class_id: uuid.UUID = Form(),
    confirmed_student_ids: list[uuid.UUID] = Form(default=[]),
    expected_class_ids: list[str] = Form(default=[]),
    file: UploadFile = File(),
):
    rows = await _uploaded_rows(file)
    target = _import_target(db, class_id)
    preview = _build_import_preview(db, rows, target)
    confirmation_ids = {row.student_id for row in preview.rows if row.status == "needs_confirmation"}
    approved_ids = set(confirmed_student_ids)
    if not approved_ids <= confirmation_ids:
        raise HTTPException(status.HTTP_409_CONFLICT, "A matrícula mudou desde a prévia. Gere uma nova prévia.")
    if len(confirmed_student_ids) != len(expected_class_ids) or len(approved_ids) != len(confirmed_student_ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Confirmações de transferência inválidas.")
    expected_by_student: dict[uuid.UUID, uuid.UUID | None] = {}
    preview_by_student = {
        row.student_id: row for row in preview.rows if row.status == "needs_confirmation"
    }
    for student_id, expected_class_id in zip(confirmed_student_ids, expected_class_ids):
        try:
            expected = uuid.UUID(expected_class_id) if expected_class_id else None
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Confirmações de transferência inválidas."
            ) from exc
        if preview_by_student[student_id].current_class_id != expected:
            raise HTTPException(status.HTTP_409_CONFLICT, "A matrícula mudou desde a prévia. Gere uma nova prévia.")
        expected_by_student[student_id] = expected

    created_count = enrolled_count = transferred_count = ignored_count = duplicate_count = 0
    try:
        for source, item in zip(rows, preview.rows):
            if item.status == "duplicate":
                duplicate_count += 1
            elif item.status in {"invalid", "ambiguous", "inactive", "already_enrolled"}:
                ignored_count += 1
            elif item.status == "needs_confirmation":
                if item.student_id not in approved_ids:
                    ignored_count += 1
                    continue
                if item.student_id is None:
                    raise HTTPException(
                        status.HTTP_409_CONFLICT, "A matrícula mudou desde a prévia. Gere uma nova prévia."
                    )
                student = db.scalar(
                    select(Student).where(Student.id == item.student_id).with_for_update()
                )
                if student is None or not student.active:
                    ignored_count += 1
                    continue
                current = db.scalar(
                    select(Enrollment).where(
                        Enrollment.student_id == student.id,
                        Enrollment.academic_year_id == target.academic_year_id,
                        Enrollment.ended_at.is_(None),
                    ).with_for_update()
                )
                current_class_id = current.class_id if current is not None else None
                if current_class_id != expected_by_student[item.student_id]:
                    raise HTTPException(
                        status.HTTP_409_CONFLICT,
                        "A matrícula mudou desde a prévia. Gere uma nova prévia.",
                    )
                _enroll(db, student, target.id)
                if item.current_class_id is None:
                    enrolled_count += 1
                else:
                    transferred_count += 1
                audit(db, user, "enroll", "student", student.id, f"bulk_import; class={target.id}")
            elif item.status == "new":
                if source.full_name is None:
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_CONTENT, "A planilha contém uma linha sem nome."
                    )
                student = Student(
                    full_name=source.full_name,
                    school_identifier=generated_school_identifier(),
                )
                db.add(student)
                db.flush()
                _enroll(db, student, target.id)
                created_count += 1
                enrolled_count += 1
                audit(db, user, "create", "student", student.id, "bulk_import")
                audit(db, user, "enroll", "student", student.id, f"bulk_import; class={target.id}")
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A matrícula mudou durante a importação. Atualize a prévia e tente novamente.",
        ) from exc

    return StudentImportResult(
        created_count=created_count, enrolled_count=enrolled_count, transferred_count=transferred_count,
        ignored_count=ignored_count, duplicate_count=duplicate_count,
    )


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
