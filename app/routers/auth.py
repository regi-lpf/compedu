from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.audit import audit
from app.config import settings
from app.deps import CurrentUser, Db
from app.models import TeachingAssignment, User
from app.policies import active_year
from app.schemas import AuthConfig, GoogleLoginRequest, LoginRequest, Me, TokenResponse
from app.security import GoogleTokenError, create_access_token, verify_google_credential, verify_password
from app.serializers import user_classes

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config", response_model=AuthConfig)
def auth_config():
    """Informa ao frontend quais métodos de login estão habilitados."""
    return AuthConfig(google_client_id=settings.google_client_id, dev_login_enabled=settings.auth_dev_login,
                      allowed_domain=settings.allowed_domain)


@router.post("/google", response_model=TokenResponse)
def login_google(payload: GoogleLoginRequest, db: Db):
    try:
        claims = verify_google_credential(payload.credential)
    except GoogleTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc))
    email = str(claims.get("email", "")).lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user or not user.active:
        # Não há auto-cadastro: o perfil (papel, nível, vínculos) é criado pela administração.
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Conta não cadastrada ou inativa no CompEdu. Procure a administração.")
    audit(db, user, "login", "user", user.id, "google")
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login_dev(payload: LoginRequest, db: Db):
    """Login por senha — habilitado quando AUTH_DEV_LOGIN=true."""
    if not settings.auth_dev_login:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Login por senha desabilitado")
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
