import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select, update

from app.audit import audit
from app.deps import AdminUser, CurrentUser, Db, forbidden, not_found
from app.models import AcademicYear, Enrollment, PedagogicalRecord, RecordType, SchoolClass
from app.policies import (
    COUNCIL_EDITORS, REPORT_GLOBAL, active_year, ensure_can_view_report, scope_classes, scope_records,
)
from app.schemas import (
    AcademicYearCreate, AcademicYearRead, AcademicYearUpdate, ClassCreate, ClassRead, ClassReport, ClassUpdate,
)

router = APIRouter(tags=["turmas"])


# ---------- Anos letivos ----------
@router.get("/academic-years", response_model=list[AcademicYearRead])
def list_years(db: Db, _user: CurrentUser):
    return db.scalars(select(AcademicYear).order_by(AcademicYear.year_label.desc())).all()


def _activate(db: Db, year: AcademicYear) -> None:
    db.execute(update(AcademicYear).where(AcademicYear.id != year.id).values(is_active=False))
    year.is_active = True


@router.post("/academic-years", response_model=AcademicYearRead, status_code=201)
def create_year(payload: AcademicYearCreate, db: Db, admin: AdminUser):
    if db.scalar(select(AcademicYear.id).where(AcademicYear.year_label == payload.year_label)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ano letivo já cadastrado")
    year = AcademicYear(year_label=payload.year_label, is_active=False)
    db.add(year)
    db.flush()
    if payload.is_active:
        _activate(db, year)
    audit(db, admin, "create", "academic_year", year.id, year.year_label)
    db.commit()
    return year


@router.patch("/academic-years/{year_id}", response_model=AcademicYearRead)
def update_year(year_id: uuid.UUID, payload: AcademicYearUpdate, db: Db, user: CurrentUser):
    year = db.get(AcademicYear, year_id)
    if not year:
        raise not_found("Ano letivo")
    fields = payload.model_fields_set
    if user.role.value != "admin":
        # Coordenação pode apenas agendar o conselho de classe.
        if user.role not in COUNCIL_EDITORS or fields - {"council_date"}:
            raise forbidden("Seu perfil não pode alterar o ano letivo")
    if "year_label" in fields and payload.year_label:
        year.year_label = payload.year_label
    if "council_date" in fields:
        year.council_date = payload.council_date
    if payload.is_active is True:
        _activate(db, year)
    elif payload.is_active is False:
        year.is_active = False
    audit(db, user, "update", "academic_year", year.id, ",".join(sorted(fields)))
    db.commit()
    return year


# ---------- Turmas ----------
def _class_reads(db: Db, user: CurrentUser, classes: list[SchoolClass]) -> list[ClassRead]:
    ids = [c.id for c in classes]
    if not ids:
        return []
    students = dict(db.execute(select(Enrollment.class_id, func.count()).where(
        Enrollment.class_id.in_(ids), Enrollment.ended_at.is_(None)).group_by(Enrollment.class_id)).all())
    records = dict(db.execute(scope_records(
        select(PedagogicalRecord.class_id, func.count()).where(PedagogicalRecord.class_id.in_(ids)), user
    ).group_by(PedagogicalRecord.class_id)).all())
    return [ClassRead(id=c.id, name=c.name, grade_level=c.grade_level, academic_year_id=c.academic_year_id,
                      year_label=c.academic_year.year_label, student_count=students.get(c.id, 0),
                      record_count=records.get(c.id, 0)) for c in classes]


@router.get("/classes", response_model=list[ClassRead])
def list_classes(db: Db, user: CurrentUser, academic_year_id: uuid.UUID | None = None):
    if academic_year_id is None:
        year = active_year(db)
        if not year:
            return []
        academic_year_id = year.id
    stmt = scope_classes(select(SchoolClass).where(SchoolClass.academic_year_id == academic_year_id), user)
    return _class_reads(db, user, list(db.scalars(stmt.order_by(SchoolClass.name))))


@router.post("/classes", response_model=ClassRead, status_code=201)
def create_class(payload: ClassCreate, db: Db, admin: AdminUser):
    year_id = payload.academic_year_id
    if year_id is None:
        year = active_year(db)
        if not year:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Cadastre e ative um ano letivo primeiro")
        year_id = year.id
    elif not db.get(AcademicYear, year_id):
        raise not_found("Ano letivo")
    if db.scalar(select(SchoolClass.id).where(SchoolClass.academic_year_id == year_id,
                                              SchoolClass.name == payload.name.strip())):
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma turma com esse nome neste ano letivo")
    item = SchoolClass(name=payload.name.strip(), grade_level=payload.grade_level, academic_year_id=year_id)
    db.add(item)
    db.flush()
    audit(db, admin, "create", "class", item.id, item.name)
    db.commit()
    db.refresh(item)
    return _class_reads(db, admin, [item])[0]


@router.patch("/classes/{class_id}", response_model=ClassRead)
def update_class(class_id: uuid.UUID, payload: ClassUpdate, db: Db, admin: AdminUser):
    item = db.get(SchoolClass, class_id)
    if not item:
        raise not_found("Turma")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    audit(db, admin, "update", "class", item.id, item.name)
    db.commit()
    return _class_reads(db, admin, [item])[0]


@router.get("/classes/{class_id}/report", response_model=ClassReport)
def class_report(class_id: uuid.UUID, db: Db, user: CurrentUser):
    """Relatório agregado (somente contagens). Admin/coordenação: todos os registros da turma."""
    item = db.get(SchoolClass, class_id)
    if not item:
        raise not_found("Turma")
    ensure_can_view_report(db, user, class_id)
    stmt = select(PedagogicalRecord.record_type, func.count()).where(PedagogicalRecord.class_id == class_id)
    if user.role in REPORT_GLOBAL:
        stmt = stmt.where(PedagogicalRecord.deleted_at.is_(None))
    else:
        stmt = scope_records(stmt, user)
    counts = dict(db.execute(stmt.group_by(PedagogicalRecord.record_type)).all())
    by_type = {t: counts.get(t, 0) for t in RecordType}
    student_count = db.scalar(select(func.count()).select_from(Enrollment).where(
        Enrollment.class_id == class_id, Enrollment.ended_at.is_(None))) or 0
    return ClassReport(class_id=item.id, class_name=item.name, year_label=item.academic_year.year_label,
                       student_count=student_count, total=sum(by_type.values()), by_type=by_type)
