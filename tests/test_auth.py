import uuid

from alembic import command

from app import security
from app.config import settings
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


def test_dev_login(client, world, monkeypatch):
    ok = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "SenhaTeste12345"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    assert client.post("/api/auth/login", json={"email": "admin@example.com", "password": "errada"}).status_code == 401
    # Conta sem senha (apenas Google) não entra por senha.
    assert client.post("/api/auth/login", json={"email": "t1@example.com", "password": "qualquer"}).status_code == 401
    monkeypatch.setattr(settings, "auth_dev_login", False)
    assert client.post("/api/auth/login", json={"email": "admin@example.com",
                                                "password": "SenhaTeste12345"}).status_code == 404


def test_auth_config(client):
    cfg = client.get("/api/auth/config").json()
    assert cfg["google_client_id"] == "test-client-id" and cfg["dev_login_enabled"] is True


def test_google_settings_load_environment_variables(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "configured-client-id")
    monkeypatch.setenv("ALLOWED_DOMAIN", "escola.edu.br")
    monkeypatch.setenv("AUTH_DEV_LOGIN", "true")

    configured = Settings(_env_file=None)

    assert configured.google_client_id == "configured-client-id"
    assert configured.allowed_domain == "escola.edu.br"
    assert configured.auth_dev_login is True


def test_google_login_maps_to_registered_profile(client, world, monkeypatch):
    def fake_verify(credential):
        if credential == "token-invalido-xx":
            raise security.GoogleTokenError("Token do Google inválido")
        return {"email": credential.removeprefix("ok:"), "email_verified": True}

    monkeypatch.setattr("app.routers.auth.verify_google_credential", fake_verify)
    ok = client.post("/api/auth/google", json={"credential": "ok:T1@example.com"})
    assert ok.status_code == 200
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {ok.json()['access_token']}"}).json()
    assert me["email"] == "t1@example.com"
    assert client.post("/api/auth/google", json={"credential": "ok:intruso@gmail.com"}).status_code == 403
    assert client.post("/api/auth/google", json={"credential": "token-invalido-xx"}).status_code == 401


def test_google_verifier_enforces_domain(monkeypatch):
    import google.oauth2.id_token as id_token

    monkeypatch.setattr(id_token, "verify_oauth2_token",
                        lambda *a, **k: {"email": "x@gmail.com", "email_verified": True, "hd": None})
    monkeypatch.setattr(settings, "allowed_domain", "escola.edu.br")
    try:
        security.verify_google_credential("abc")
        raise AssertionError("deveria rejeitar domínio")
    except security.GoogleTokenError as exc:
        assert "institucional" in str(exc)


def test_production_settings_validation():
    import pytest
    from app.config import Settings

    with pytest.raises(ValueError):
        Settings(environment="prod", database_url="postgresql://u:p@h/db")
    s = Settings(environment="prod", secret_key="x" * 40, database_url="postgres://u:p@h/db")
    assert s.sqlalchemy_url.startswith("postgresql+psycopg://")


def test_password_login_is_never_enabled_in_production(client, monkeypatch):
    monkeypatch.setattr(settings, "environment", "prod")
    monkeypatch.setattr(settings, "auth_dev_login", True)
    assert settings.dev_login_enabled is False
    assert client.get("/api/auth/config").json()["dev_login_enabled"] is False
    assert client.post("/api/auth/login", json={
        "email": "admin@example.com",
        "password": "SenhaTeste12345",
    }).status_code == 404


def test_migrations_match_models(tmp_path):
    cfg = alembic_config()
    cfg.attributes["database_url"] = f"sqlite:///{tmp_path / 'mig.db'}"
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    command.check(cfg)  # falha se os modelos divergirem das migrações
