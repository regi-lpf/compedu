"""Cria a primeira conta administrativa.

Uso: python -m app.create_admin
Em produção, use uma conta Google institucional; não crie senha local.
"""
from getpass import getpass

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.migrate import upgrade_head
from app.models import Role, User
from app.security import hash_password


def validate_bootstrap_email(email: str) -> str:
    email = email.strip().lower()
    if "@" not in email:
        raise SystemExit("Informe um e-mail válido.")
    if settings.allowed_domain and not email.endswith("@" + settings.allowed_domain.lower()):
        raise SystemExit("O e-mail do administrador deve pertencer ao domínio institucional configurado.")
    return email


def main() -> None:
    upgrade_head()
    name = input("Nome do administrador: ").strip()
    email = validate_bootstrap_email(input("E-mail (institucional/Google): "))
    password = None
    if settings.environment != "prod":
        password = getpass("Senha para login local (Enter para pular; mínimo 12 caracteres): ")
        if password and len(password) < 12:
            raise SystemExit("A senha deve ter pelo menos 12 caracteres.")
    with SessionLocal() as db:
        active_admin = db.scalar(select(User.id).where(User.role == Role.admin, User.active.is_(True)).limit(1))
        if active_admin:
            raise SystemExit("Já existe um administrador ativo. Use a administração pela interface.")
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("Já existe uma conta com esse e-mail.")
        db.add(User(name=name, email=email, password_hash=hash_password(password) if password else None,
                    role=Role.admin, access_level=1))
        db.commit()
    print("Conta administrativa criada.")


if __name__ == "__main__":
    main()
