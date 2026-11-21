import uuid
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.config import settings

password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
    if not hashed:
        # Executa um hash mesmo assim para não revelar, por tempo de resposta, contas sem senha.
        password_hash.hash(password)
        return False
    return password_hash.verify(password, hashed)


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=settings.access_token_minutes)}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID:
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM], options={"require": ["sub", "exp"]})
    return uuid.UUID(payload["sub"])


class GoogleTokenError(Exception):
    pass


def verify_google_credential(credential: str) -> dict:
    """Valida o ID token emitido pelo Google Identity Services e devolve as claims."""
    if not settings.google_client_id:
        raise GoogleTokenError("Login com Google não configurado")
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    try:
        claims = id_token.verify_oauth2_token(credential, google_requests.Request(), settings.google_client_id)
    except ValueError as exc:
        raise GoogleTokenError("Token do Google inválido") from exc
    if not claims.get("email_verified"):
        raise GoogleTokenError("E-mail Google não verificado")
    if settings.allowed_domain and claims.get("hd") != settings.allowed_domain:
        raise GoogleTokenError("Use sua conta institucional")
    return claims
