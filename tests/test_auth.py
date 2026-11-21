import uuid

from alembic import command

from app import security
from app.migrate import alembic_config


def test_me_returns_profile_and_active_year_classes(client, world):
    me = client.get("/api/auth/me", headers=world.h("t1")).json()
    assert me["role"] == "teacher" and me["access_level"] == 3 and me["active_year"] == "2026"
    assert [c["name"] for c in me["classes"]] == ["A"]


def test_invalid_missing_or_inactive_token(client, world):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer lixo"}).status_code == 401
    unknown = security.create_access_token(uuid.uuid4())
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {unknown}"}).status_code == 401
    client.patch(f"/api/admin/users/{world.users['t1']}", json={"active": False}, headers=world.h("admin"))
    assert client.get("/api/auth/me", headers=world.h("t1")).status_code == 401


def test_password_login(client, world):
    ok = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "SenhaTeste12345"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    assert client.post("/api/auth/login", json={"email": "admin@example.com", "password": "errada"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "t1@example.com", "password": "qualquer"}).status_code == 401


def test_production_settings_validation():
    import pytest
    from app.config import Settings

    with pytest.raises(ValueError):
        Settings(environment="prod", database_url="postgresql://u:p@h/db")
    s = Settings(environment="prod", secret_key="x" * 40, database_url="postgres://u:p@h/db")
    assert s.sqlalchemy_url.startswith("postgresql+psycopg://")


def test_migrations_match_models(tmp_path):
    cfg = alembic_config()
    cfg.attributes["database_url"] = f"sqlite:///{tmp_path / 'mig.db'}"
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    command.check(cfg)  # falha se os modelos divergirem das migrações
