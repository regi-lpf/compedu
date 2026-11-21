import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.audit import audit
from app.deps import CurrentUser, Db, not_found
from app.models import Announcement
from app.policies import ensure_announcement_writer, ensure_can_manage_announcement, ensure_publish_level
from app.schemas import AnnouncementCreate, AnnouncementRead, AnnouncementUpdate
from app.serializers import announcement_read

router = APIRouter(prefix="/announcements", tags=["mural"])


def _visible_stmt(user: CurrentUser):
    return (select(Announcement).options(joinedload(Announcement.author))
            .where(Announcement.deleted_at.is_(None), Announcement.access_level >= user.access_level))


def _visible(db: Db, user: CurrentUser, item_id: uuid.UUID) -> Announcement:
    item = db.scalar(_visible_stmt(user).where(Announcement.id == item_id))
    if not item:
        raise not_found("Comunicado")
    return item


@router.get("", response_model=list[AnnouncementRead])
def list_announcements(db: Db, user: CurrentUser, limit: int = Query(default=100, ge=1, le=500),
                       offset: int = Query(default=0, ge=0)):
    stmt = _visible_stmt(user).order_by(Announcement.published_at.desc(), Announcement.id).limit(limit).offset(offset)
    return [announcement_read(a) for a in db.scalars(stmt).all()]


@router.post("", response_model=AnnouncementRead, status_code=201)
def create_announcement(payload: AnnouncementCreate, db: Db, user: CurrentUser):
    ensure_announcement_writer(user)
    ensure_publish_level(user, payload.access_level)
    item = Announcement(**payload.model_dump(), author_id=user.id)
    db.add(item)
    db.flush()
    audit(db, user, "create", "announcement", item.id)
    db.commit()
    return announcement_read(_visible(db, user, item.id))


@router.patch("/{item_id}", response_model=AnnouncementRead)
def update_announcement(item_id: uuid.UUID, payload: AnnouncementUpdate, db: Db, user: CurrentUser):
    item = _visible(db, user, item_id)
    ensure_can_manage_announcement(user, item.author_id)
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "access_level" in data:
        ensure_publish_level(user, data["access_level"])
    for key, value in data.items():
        setattr(item, key, value)
    item.updated_at = datetime.now(timezone.utc)
    audit(db, user, "update", "announcement", item.id, ",".join(sorted(data)))
    db.commit()
    return announcement_read(_visible(db, user, item.id))


@router.delete("/{item_id}", status_code=204)
def delete_announcement(item_id: uuid.UUID, db: Db, user: CurrentUser):
    item = _visible(db, user, item_id)
    ensure_can_manage_announcement(user, item.author_id)
    item.deleted_at = datetime.now(timezone.utc)
    audit(db, user, "delete", "announcement", item.id)
    db.commit()
