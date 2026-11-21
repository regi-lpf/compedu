import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.audit import audit
from app.deps import CurrentUser, Db, not_found
from app.models import PedagogicalRecord, RecordType, Student
from app.policies import (
    ensure_can_delete_record, ensure_can_edit_record, ensure_publish_level, record_target_class, scope_records,
)
from app.schemas import RecordCreate, RecordRead, RecordUpdate
from app.serializers import record_read

router = APIRouter(prefix="/records", tags=["registros"])

_OPTS = (joinedload(PedagogicalRecord.student), joinedload(PedagogicalRecord.author),
         joinedload(PedagogicalRecord.school_class))


def _visible(db: Db, user: CurrentUser, record_id: uuid.UUID) -> PedagogicalRecord:
    record = db.scalar(scope_records(select(PedagogicalRecord).options(*_OPTS)
                                     .where(PedagogicalRecord.id == record_id), user))
    if not record:
        raise not_found("Registro")
    return record


@router.get("", response_model=list[RecordRead])
def list_records(db: Db, user: CurrentUser, class_id: uuid.UUID | None = None, student_id: uuid.UUID | None = None,
                 record_type: RecordType | None = None, limit: int = Query(default=100, ge=1, le=500),
                 offset: int = Query(default=0, ge=0)):
    stmt = scope_records(select(PedagogicalRecord).options(*_OPTS), user)
    if class_id is not None:
        stmt = stmt.where(PedagogicalRecord.class_id == class_id)
    if student_id is not None:
        stmt = stmt.where(PedagogicalRecord.student_id == student_id)
    if record_type is not None:
        stmt = stmt.where(PedagogicalRecord.record_type == record_type)
    stmt = stmt.order_by(PedagogicalRecord.created_at.desc(), PedagogicalRecord.id).limit(limit).offset(offset)
    return [record_read(r) for r in db.scalars(stmt).all()]


@router.post("", response_model=RecordRead, status_code=201)
def create_record(payload: RecordCreate, db: Db, user: CurrentUser):
    student = db.get(Student, payload.student_id)
    if not student or not student.active:
        raise not_found("Aluno")
    class_id = record_target_class(db, user, student)
    ensure_publish_level(user, payload.access_level)
    record = PedagogicalRecord(**payload.model_dump(), author_id=user.id, class_id=class_id)
    db.add(record)
    db.flush()
    audit(db, user, "create", "record", record.id)
    db.commit()
    return record_read(_visible(db, user, record.id))


@router.patch("/{record_id}", response_model=RecordRead)
def update_record(record_id: uuid.UUID, payload: RecordUpdate, db: Db, user: CurrentUser):
    record = _visible(db, user, record_id)
    ensure_can_edit_record(user, record)
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "access_level" in data:
        ensure_publish_level(user, data["access_level"])
    for key, value in data.items():
        setattr(record, key, value)
    record.updated_at = datetime.now(timezone.utc)
    audit(db, user, "update", "record", record.id, ",".join(sorted(data)))
    db.commit()
    return record_read(_visible(db, user, record.id))


@router.delete("/{record_id}", status_code=204)
def delete_record(record_id: uuid.UUID, db: Db, user: CurrentUser):
    record = _visible(db, user, record_id)
    ensure_can_delete_record(user, record)
    record.deleted_at = datetime.now(timezone.utc)  # exclusão lógica: preserva histórico e auditoria
    audit(db, user, "delete", "record", record.id)
    db.commit()
