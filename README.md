# CompEdu

Aplicação web de apoio à gestão escolar estruturada em torno de dois pilares: **mural interno de comunicados** e **registros pedagógicos**, com controle de acesso híbrido (níveis verticais de 1 a 5 e vínculos horizontais por papel, turma e ano letivo).

A arquitetura detalhada, matriz de permissões e diagramas UML estão em [docs/arq-decisoes-final.md](docs/arq-decisoes-final.md) e as decisões de produto em [docs/decisoes-produto.md](docs/decisoes-produto.md).

## Estrutura do projeto

- `app/` — Backend FastAPI, modelos SQLAlchemy 2.0 (UUID), política centralizada de autorização (`app/policies.py`) e routers REST (`app/routers/`).
- `migrations/` — Migrações de banco de dados gerenciadas pelo Alembic.
- `frontend/` — Aplicação SPA estática (HTML, CSS e JS puro) integrada à API.
- `api/index.py` e `vercel.json` — Entrypoint Serverless e configuração de roteamento para deploy na Vercel.
- `tests/` — Suíte de testes automatizados (pytest) cobrindo a matriz de autorização, autenticação Google/local, matrículas e migrações.
- `docs/` — Documentação arquitetural, decisões de produto e mockups originais (`docs/mockups/`).

## Executando localmente

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m app.seed_demo
uvicorn app.main:app --reload
```

### Windows (PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m app.seed_demo
uvicorn app.main:app --reload
```

Se `DATABASE_URL` não estiver definida, o sistema utiliza SQLite local (`compedu.db`) para desenvolvimento rápido.

Acesse:
- `http://127.0.0.1:8000` — Aplicação web CompEdu
- `http://127.0.0.1:8000/docs` — Documentação interativa OpenAPI (Swagger)
- `http://127.0.0.1:8000/api/health` — Verificação de saúde do serviço

### Contas fictícias criadas por `python -m app.seed_demo`

Todos os dados gerados pelo seed são exclusivamente fictícios. Na tela de login, você também pode clicar nos atalhos de demonstração:

| Papel | Nível | E-mail | Senha |
| :--- | :---: | :--- | :--- |
| Administração | `1` | `admin@example.com` | `DemoAdmin2026!` |
| Coordenação | `2` | `coord@example.com` | `DemoCoord2026!` |
| Professora (2º A e 3º A) | `3` | `prof@example.com` | `DemoProf2026!` |
| Professor B (2º B) | `3` | `prof2@example.com` | `DemoProf2026!` |
| Secretaria | `4` | `secretaria@example.com` | `DemoSecre2026!` |
| Suporte técnico | `5` | `suporte@example.com` | `DemoSuporte2026!` |

### Usando PostgreSQL local via Docker

```bash
cp .env.example .env
docker compose up -d db
python -m app.migrate
python -m app.create_admin
```

## Executando os testes

```bash
pytest
```

## Deploy na Vercel (Frontend Estático + FastAPI Serverless + Postgres)

1. Crie um banco PostgreSQL gerenciado (Neon, Supabase ou Vercel Postgres).
2. Configure as variáveis de ambiente no projeto da Vercel:
   - `ENVIRONMENT=prod`
   - `DATABASE_URL=postgresql://...` (a aplicação normaliza automaticamente para `postgresql+psycopg://` e usa `NullPool` em ambiente serverless)
   - `SECRET_KEY=<segredo aleatório com pelo menos 32 caracteres>`
   - `GOOGLE_CLIENT_ID=<Client ID OAuth 2.0 Web do Google Cloud Console>`
   - `ALLOWED_DOMAIN=<opcional, ex.: escola.edu.br>`
   - `AUTH_DEV_LOGIN=false`
3. Aplique as migrações no banco de produção e cadastre o administrador inicial:
   ```bash
   DATABASE_URL="postgresql://..." python -m app.migrate
   DATABASE_URL="postgresql://..." python -m app.create_admin
   ```
4. Faça o deploy na Vercel (`vercel --prod` ou integração Git). O `vercel.json` publica `frontend/` na CDN e encaminha `/api/*` para a Function Python em `api/index.py`.
