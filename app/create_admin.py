"""Cria a primeira conta administrativa.

Uso: python -m app.create_admin
Com login Google, a senha é opcional (deixe em branco); ela só é usada quando AUTH_DEV_LOGIN=true.
"""
from getpass import getpass

from sqlalchemy import select

from app.database import SessionLocal
from app.migrate import upgrade_head
from app.models import Role, User
from app.security import hash_password


def main() -> None:
    upgrade_head()
    name = input("Nome do administrador: ").strip()
    email = input("E-mail (institucional/Google): ").strip().lower()
    password = getpass("Senha para login local (Enter para pular; mínimo 12 caracteres): ")
    if password and len(password) < 12:
        raise SystemExit("A senha deve ter pelo menos 12 caracteres.")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("Já existe uma conta com esse e-mail.")
        db.add(User(name=name, email=email, password_hash=hash_password(password) if password else None,
                    role=Role.admin, access_level=1))
        db.commit()
    print("Conta administrativa criada.")


if __name__ == "__main__":
    main()
