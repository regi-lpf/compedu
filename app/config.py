from functools import cached_property
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "development-only-change-this-secret-0123456789"
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    environment: Literal["dev", "test", "prod"] = "dev"
    database_url: str = f"sqlite:///{BASE_DIR / 'compedu.db'}"
    secret_key: str = DEV_SECRET
    access_token_minutes: int = 60
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    # Autenticação
    google_client_id: str = ""
    allowed_domain: str = ""  # ex.: escola.edu.br — vazio aceita qualquer domínio verificado pelo Google
    auth_dev_login: bool = True  # login por e-mail/senha; desligue em produção se quiser só Google

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    @model_validator(mode="after")
    def _check_production(self) -> "Settings":
        if self.environment == "prod":
            if self.secret_key == DEV_SECRET or len(self.secret_key) < 32:
                raise ValueError("Em produção, defina SECRET_KEY com pelo menos 32 caracteres aleatórios.")
            if self.database_url.startswith("sqlite"):
                raise ValueError("Em produção, use PostgreSQL (DATABASE_URL).")
        return self

    @cached_property
    def sqlalchemy_url(self) -> str:
        """Normaliza URLs de provedores (Neon/Supabase/Vercel) para o driver psycopg 3."""
        url = self.database_url
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
