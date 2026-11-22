import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.audit import audit
from app.deps import AdminUser, Db, not_found
from app.config import settings
from app.models import DEFAULT_LEVEL, Role, SchoolClass, TeachingAssignment, User
from app.policies import active_year
from app.schemas import AssignmentsUpdate, UserCreate, UserRead, UserUpdate
from app.security import hash_password
from app.serializers import user_read

router = APIRouter(prefix="/admin/users", tags=["admin"])


def _validate_institutional_email(email: str) -> str:
    email = email.strip().lower()
    if settings.environment == "prod" and settings.allowed_domain:
        if not email.endswith("@" + settings.allowed_domain.lower()):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                                "Use um e-mail do domínio institucional configurado")
    return email


def _active_admin_count(db: Session) -> int:
    return db.scalar(select(func.count(User.id)).where(User.role == Role.admin, User.active.is_(True))) or 0


def _load(db: Db, user_id: uuid.UUID) -> User:
    user = db.scalar(select(User).options(selectinload(User.assignments).selectinload(TeachingAssignment.school_class))
                     .where(User.id == user_id))
    if not user:
        raise not_found("Usuário")
    return user


def _replace_assignments(db: Db, user: User, class_ids: list[uuid.UUID], year_id: uuid.UUID) -> None:
    ids = set(class_ids)
    classes = list(db.scalars(select(SchoolClass).where(SchoolClass.id.in_(ids)))) if ids else []
    if len(classes) != len(ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Uma ou mais turmas não existem")
    if any(c.academic_year_id != year_id for c in classes):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Todas as turmas devem pertencer ao mesmo ano letivo")
    year_class_ids = select(SchoolClass.id).where(SchoolClass.academic_year_id == year_id)
    db.execute(delete(TeachingAssignment).where(TeachingAssignment.user_id == user.id,
                                                TeachingAssignment.class_id.in_(year_class_ids)))
    db.add_all([TeachingAssignment(user_id=user.id, class_id=c.id) for c in classes])


@router.get("", response_model=list[UserRead])
def list_users(db: Db, _admin: AdminUser):
    year = active_year(db)
    users = db.scalars(select(User).options(selectinload(User.assignments).selectinload(TeachingAssignment.school_class))
                       .order_by(User.name)).all()
    return [user_read(u, year.id if year else None) for u in users]


@router.post("", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, db: Db, admin: AdminUser):
    email = _validate_institutional_email(str(payload.email))
    if settings.environment == "prod" and payload.password:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Senhas locais não são permitidas em produção")
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail já cadastrado")
    user = User(name=payload.name.strip(), email=email, role=payload.role,
                access_level=payload.access_level or DEFAULT_LEVEL[payload.role],
                password_hash=hash_password(payload.password) if payload.password else None)
    db.add(user)
    db.flush()
    year = active_year(db)
    if payload.class_ids:
        if not year:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Não há ano letivo ativo para vincular turmas")
        _replace_assignments(db, user, payload.class_ids, year.id)
    audit(db, admin, "create", "user", user.id, f"role={user.role.value} level={user.access_level}")
    db.commit()
    return user_read(_load(db, user.id), year.id if year else None)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: uuid.UUID, payload: UserUpdate, db: Db, admin: AdminUser):
    user = _load(db, user_id)
    data = payload.model_dump(exclude_unset=True)
    if user.id == admin.id and (data.get("active") is False or data.get("role") not in (None, admin.role)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Você não pode desativar ou rebaixar a própria conta")
    proposed_role = data.get("role", user.role)
    proposed_active = data.get("active", user.active)
    if (user.role == Role.admin and user.active
            and _active_admin_count(db) <= 1
            and (proposed_role != Role.admin or not proposed_active)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Não é possível remover o último administrador ativo")
    if "password" in data:
        pw = data.pop("password")
        if settings.environment == "prod" and pw:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                                "Senhas locais não são permitidas em produção")
        user.password_hash = hash_password(pw) if pw else None
    if "role" in data and "access_level" not in data:
        data["access_level"] = DEFAULT_LEVEL[data["role"]]
    for key, value in data.items():
        setattr(user, key, value)
    audit(db, admin, "update", "user", user.id, ",".join(sorted(payload.model_fields_set)))
    db.commit()
    year = active_year(db)
    return user_read(_load(db, user.id), year.id if year else None)


@router.put("/{user_id}/assignments", response_model=UserRead)
def set_assignments(user_id: uuid.UUID, payload: AssignmentsUpdate, db: Db, admin: AdminUser,
                    academic_year_id: uuid.UUID | None = None):
    """Substitui os vínculos do profissional com as turmas de um ano letivo (padrão: ano ativo)."""
    user = _load(db, user_id)
    year = active_year(db)
    year_id = academic_year_id or (year.id if year else None)
    if year_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Não há ano letivo ativo")
    _replace_assignments(db, user, payload.class_ids, year_id)
    audit(db, admin, "assign", "user", user.id, f"{len(payload.class_ids)} turma(s)")
    db.commit()
    db.expire(user)
    return user_read(_load(db, user.id), year.id if year else None)
