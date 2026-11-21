from datetime import datetime, timezone

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.deps import CurrentUser, Db, forbidden
from app.models import AuditLog, Enrollment, PedagogicalRecord, RecordType, SchoolClass, Student
from app.policies import AUDIT_READERS, active_year, scope_classes, scope_records, scope_students
from app.schemas import AuditRead, Dashboard, WatchItem
from app.serializers import record_read

router = APIRouter(tags=["painel"])


@router.get("/dashboard", response_model=Dashboard)
def dashboard(db: Db, user: CurrentUser):
    """Indicadores do painel, sempre calculados dentro do escopo do usuário."""
    year = active_year(db)
    if year is None:
        return Dashboard(student_count=0, class_count=0, records_this_month=0, council_date=None, active_year=None,
                         recent_records=[], watch_students=[])

    enrolled = select(Enrollment.student_id).where(Enrollment.academic_year_id == year.id, Enrollment.ended_at.is_(None))
    student_count = db.scalar(scope_students(select(func.count(Student.id)).where(Student.id.in_(enrolled)), user)) or 0
    class_count = db.scalar(scope_classes(select(func.count(SchoolClass.id))
                                          .where(SchoolClass.academic_year_id == year.id), user)) or 0

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    records_this_month = db.scalar(scope_records(select(func.count(PedagogicalRecord.id))
                                                 .where(PedagogicalRecord.created_at >= month_start), user)) or 0

    recent = db.scalars(scope_records(select(PedagogicalRecord).options(
        joinedload(PedagogicalRecord.student), joinedload(PedagogicalRecord.author),
        joinedload(PedagogicalRecord.school_class)), user)
        .order_by(PedagogicalRecord.created_at.desc()).limit(5)).all()

    watch_rows = db.execute(scope_records(
        select(PedagogicalRecord.student_id, func.count().label("n"))
        .where(PedagogicalRecord.record_type == RecordType.attention), user)
        .group_by(PedagogicalRecord.student_id).order_by(func.count().desc()).limit(5)).all()
    watch: list[WatchItem] = []
    for student_id, n in watch_rows:
        student = db.get(Student, student_id)
        cls = db.scalar(select(SchoolClass.name).join(Enrollment, Enrollment.class_id == SchoolClass.id).where(
            Enrollment.student_id == student_id, Enrollment.academic_year_id == year.id, Enrollment.ended_at.is_(None)))
        watch.append(WatchItem(student_id=student_id, student_name=student.full_name, class_name=cls, attention_count=n))

    return Dashboard(student_count=student_count, class_count=class_count, records_this_month=records_this_month,
                     council_date=year.council_date, active_year=year.year_label,
                     recent_records=[record_read(r) for r in recent], watch_students=watch)


@router.get("/audit", response_model=list[AuditRead])
def list_audit(db: Db, user: CurrentUser, limit: int = Query(default=100, ge=1, le=500)):
    if user.role not in AUDIT_READERS:
        raise forbidden("Seu perfil não pode consultar a auditoria")
    rows = db.scalars(select(AuditLog).options(joinedload(AuditLog.actor))
                      .order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return [AuditRead(id=r.id, actor_name=r.actor.name if r.actor else None, action=r.action, entity=r.entity,
                      entity_id=r.entity_id, detail=r.detail, created_at=r.created_at) for r in rows]
