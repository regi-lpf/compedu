from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.audit import audit
from app.deps import CurrentUser, Db
from app.models import TeachingAssignment, User
from app.policies import active_year
from app.schemas import LoginRequest, Me, TokenResponse
from app.security import create_access_token, verify_password
from app.serializers import user_classes

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Db):
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha inválidos")
    audit(db, user, "login", "user", user.id, "password")
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=Me)
def me(user: CurrentUser, db: Db):
    year = active_year(db)
    user = db.scalar(select(User).options(selectinload(User.assignments).selectinload(TeachingAssignment.school_class))
                     .where(User.id == user.id).execution_options(populate_existing=True))
    return Me(id=user.id, name=user.name, email=user.email, role=user.role, access_level=user.access_level,
              classes=user_classes(user, year.id if year else None), active_year=year.year_label if year else None)
