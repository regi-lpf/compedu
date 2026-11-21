"""Aplica as migrações Alembic programaticamente (python -m app.migrate)."""
from alembic import command
from alembic.config import Config

from app.config import BASE_DIR


def alembic_config() -> Config:
    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "migrations"))
    return cfg


def upgrade_head() -> None:
    command.upgrade(alembic_config(), "head")


if __name__ == "__main__":
    upgrade_head()
    print("Banco atualizado para a última migração.")
