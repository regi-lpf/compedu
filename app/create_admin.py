from getpass import getpass

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Role, User
from app.security import hash_password


def main() -> None:
    Base.metadata.create_all(bind=engine)
    name = input("Nome do administrador: ").strip()
    email = input("E-mail: ").strip().lower()
    password = getpass("Senha (mínimo 12 caracteres): ")
    if len(password) < 12:
        raise SystemExit("A senha deve ter pelo menos 12 caracteres.")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("Já existe uma conta com esse e-mail.")
        user = User(name=name, email=email, password_hash=hash_password(password), role=Role.admin, access_level=1)
        db.add(user)
        db.commit()
    print("Conta administrativa criada.")


if __name__ == "__main__":
    main()
