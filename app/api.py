from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models import Announcement, PedagogicalRecord, Role, SchoolClass, Student, User
from app.schemas import AnnouncementCreate, AnnouncementRead, ClassCreate, ClassRead, LoginRequest, RecordCreate, RecordRead, StudentCreate, StudentRead, TokenResponse, UserCreate, UserRead
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api")
Db = Annotated[Session, Depends(get_db)]
bearer = HTTPBearer(auto_error=False)
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


def current_user(credentials: Credentials, db: Db) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Autenticação necessária", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido", headers={"WWW-Authenticate": "Bearer"})
    user = db.get(User, user_id)
    if not user or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Conta inativa ou inexistente")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != Role.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ação restrita à administração")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def record_read(record: PedagogicalRecord) -> RecordRead:
    return RecordRead(
        id=record.id, student_id=record.student_id, student_name=record.student.name,
        class_id=record.student.class_id, class_name=record.student.school_class.name,
        author_name=record.author.name, kind=record.kind, access_level=record.access_level,
        body=record.body, created_at=record.created_at,
    )


def announcement_read(item: Announcement) -> AnnouncementRead:
    return AnnouncementRead(id=item.id, title=item.title, body=item.body, access_level=item.access_level,
                            author_name=item.author.name, created_at=item.created_at)


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Db):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha inválidos")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/auth/me", response_model=UserRead)
def me(user: CurrentUser):
    return UserRead(id=user.id, name=user.name, email=user.email, role=user.role,
                    access_level=user.access_level, class_ids=[c.id for c in user.classes])


@router.post("/admin/users", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, db: Db, _admin: AdminUser):
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail já cadastrado")
    classes = list(db.scalars(select(SchoolClass).where(SchoolClass.id.in_(payload.class_ids))).all()) if payload.class_ids else []
    if len(classes) != len(set(payload.class_ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Uma ou mais turmas não existem")
    user = User(name=payload.name, email=email, password_hash=hash_password(payload.password), role=payload.role,
                access_level=payload.access_level, classes=classes)
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserRead(id=user.id, name=user.name, email=user.email, role=user.role,
                    access_level=user.access_level, class_ids=[c.id for c in user.classes])


@router.get("/admin/users", response_model=list[UserRead])
def list_users(db: Db, _admin: AdminUser):
    return [UserRead(id=u.id, name=u.name, email=u.email, role=u.role, access_level=u.access_level,
                     class_ids=[c.id for c in u.classes]) for u in db.scalars(select(User).order_by(User.name)).all()]


@router.post("/classes", response_model=ClassRead, status_code=201)
def create_class(payload: ClassCreate, db: Db, _admin: AdminUser):
    item = SchoolClass(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return ClassRead(id=item.id, name=item.name, year=item.year, student_count=0)


@router.get("/classes", response_model=list[ClassRead])
def list_classes(db: Db, user: CurrentUser):
    query = select(SchoolClass).options(joinedload(SchoolClass.students)).order_by(SchoolClass.name)
    if user.role == Role.teacher:
        query = query.where(SchoolClass.id.in_([c.id for c in user.classes]))
    return [ClassRead(id=c.id, name=c.name, year=c.year, student_count=len(c.students)) for c in db.scalars(query).unique().all()]


@router.post("/students", response_model=StudentRead, status_code=201)
def create_student(payload: StudentCreate, db: Db, _admin: AdminUser):
    school_class = db.get(SchoolClass, payload.class_id)
    if not school_class:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Turma não encontrada")
    student = Student(name=payload.name, class_id=payload.class_id)
    db.add(student)
    db.commit()
    db.refresh(student)
    return StudentRead(id=student.id, name=student.name, class_id=school_class.id, class_name=school_class.name)


@router.get("/students", response_model=list[StudentRead])
def list_students(db: Db, user: CurrentUser, class_id: int | None = None):
    query = select(Student).options(joinedload(Student.school_class)).order_by(Student.name)
    if user.role == Role.teacher:
        query = query.where(Student.class_id.in_([c.id for c in user.classes]))
    if class_id is not None:
        query = query.where(Student.class_id == class_id)
    return [StudentRead(id=s.id, name=s.name, class_id=s.class_id, class_name=s.school_class.name) for s in db.scalars(query).all()]


@router.post("/records", response_model=RecordRead, status_code=201)
def create_record(payload: RecordCreate, db: Db, user: CurrentUser):
    student = db.scalar(select(Student).options(joinedload(Student.school_class)).where(Student.id == payload.student_id))
    if not student:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aluno não encontrado")
    if user.role == Role.teacher:
        if student.class_id not in {c.id for c in user.classes}:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não está vinculado à turma deste aluno")
    elif user.role == Role.secretary:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Secretaria não pode criar registros pedagógicos")
    if payload.access_level < user.access_level:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não pode publicar em um nível mais restrito que o seu")
    record = PedagogicalRecord(**payload.model_dump(), author_id=user.id)
    db.add(record)
    db.commit()
    record = db.scalar(select(PedagogicalRecord).options(joinedload(PedagogicalRecord.student).joinedload(Student.school_class), joinedload(PedagogicalRecord.author)).where(PedagogicalRecord.id == record.id))
    return record_read(record)


@router.get("/records", response_model=list[RecordRead])
def list_records(db: Db, user: CurrentUser, class_id: int | None = None, student_id: int | None = None,
                 kind: str | None = Query(default=None, pattern="^(positive|attention|follow_up)$")):
    query = select(PedagogicalRecord).options(joinedload(PedagogicalRecord.student).joinedload(Student.school_class), joinedload(PedagogicalRecord.author)).join(Student).order_by(PedagogicalRecord.created_at.desc())
    if class_id is not None:
        query = query.where(Student.class_id == class_id)
    if student_id is not None:
        query = query.where(PedagogicalRecord.student_id == student_id)
    if kind:
        query = query.where(PedagogicalRecord.kind == kind)
    query = query.where(PedagogicalRecord.access_level >= user.access_level)
    return [record_read(r) for r in db.scalars(query).unique().all()]


@router.post("/announcements", response_model=AnnouncementRead, status_code=201)
def create_announcement(payload: AnnouncementCreate, db: Db, user: CurrentUser):
    if user.role not in {Role.admin, Role.coordination, Role.secretary}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Seu perfil não pode publicar comunicados")
    if payload.access_level < user.access_level:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não pode publicar em um nível mais restrito que o seu")
    item = Announcement(**payload.model_dump(), author_id=user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    item.author = user
    return announcement_read(item)


@router.get("/announcements", response_model=list[AnnouncementRead])
def list_announcements(db: Db, user: CurrentUser):
    items = db.scalars(
        select(Announcement)
        .options(joinedload(Announcement.author))
        .where(Announcement.access_level >= user.access_level)
        .order_by(Announcement.created_at.desc())
    ).unique().all()
    return [announcement_read(item) for item in items]
