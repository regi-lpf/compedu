# CompEdu

O CompEdu é uma aplicação web para equipes escolares gerirem comunicados internos e registros pedagógicos.
O controle de acesso combina duas dimensões:

- **Eixo vertical:** níveis numéricos de 1 a 5, em que 1 é o nível mais alto.
- **Eixo horizontal:** papel, ano letivo, turma, matrícula e vínculo de ensino.

## Funcionalidades

- mural interno de comunicados;
- registros pedagógicos de estudantes;
- turmas, matrículas e histórico anual;
- importação em lote de alunos por listas CSV, XLS ou XLSX;
- perfis, papéis e níveis da equipe escolar;
- painel, relatórios e trilha de auditoria.

## Contas e autenticação

Em produção, o acesso usa Google OAuth. Depois que o Google valida o token, o sistema procura um usuário
CompEdu já cadastrado e ativo. A aplicação não cria contas automaticamente após o login.

O primeiro administrador é criado uma vez, manualmente, no banco de produção. Em seguida, administradores
gerenciam os demais usuários pela interface, incluindo papel, nível e turmas.

O login por e-mail e senha existe apenas para desenvolvimento e testes. Ele é desativado em produção.

## Executando localmente

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m app.seed_demo
uvicorn app.main:app --reload
```

Sem `DATABASE_URL`, o sistema usa SQLite local. O seed cria somente dados fictícios.

URLs locais:

- `http://127.0.0.1:8000` — aplicação
- `http://127.0.0.1:8000/docs` — documentação OpenAPI
- `http://127.0.0.1:8000/api/health` — verificação de saúde

Para PostgreSQL local com Docker:

```bash
cp .env.example .env
docker compose up -d db
python -m app.migrate
python -m app.create_admin
```

## Deploy na Vercel

1. Crie um banco PostgreSQL gerenciado.
2. Configure um OAuth 2.0 Web Client no Google Cloud para o domínio implantado.
3. Configure no projeto da Vercel:

   - `ENVIRONMENT=prod`
   - `DATABASE_URL=postgresql://...`
   - `SECRET_KEY=<segredo aleatório com pelo menos 32 caracteres>`
   - `GOOGLE_CLIENT_ID=<Google OAuth 2.0 Web Client ID>`
   - `ALLOWED_DOMAIN=<opcional; exemplo: escola.edu.br>`
   - `AUTH_DEV_LOGIN=false`

4. A partir de uma máquina segura que tenha acesso ao banco, aplique as migrações e crie o primeiro administrador:

   Linux/macOS:

   ```bash
   DATABASE_URL="postgresql://..." python -m app.migrate
   ENVIRONMENT=prod \
   DATABASE_URL="postgresql://..." \
   SECRET_KEY="<segredo aleatório com pelo menos 32 caracteres>" \
   GOOGLE_CLIENT_ID="<Google OAuth 2.0 Web Client ID>" \
   ALLOWED_DOMAIN="escola.edu.br" \
   AUTH_DEV_LOGIN=false \
   python -m app.create_admin --name "Nome do administrador" --email "admin@escola.edu.br"
   ```

   Este comando é um bootstrap manual único, não uma etapa automática do deploy. Em produção ele não aceita
   senha local e cria uma conta vinculada ao Google.

5. Entre com a conta Google institucional informada no bootstrap.
6. Use **Cadastros → Usuários** para cadastrar ou desativar a equipe e definir papéis, níveis e turmas.

O entrypoint é `api/index.py`, que exporta a aplicação FastAPI. O `vercel.json` encaminha `/api/*` para
a função Python e serve os arquivos estáticos de `frontend/`.

## Testes

```bash
python -m pytest tests/test_auth.py
python -m pytest tests/test_authorization.py
pytest -q
```

A CI usa `pytest -q` com Python 3.12.

## Stack técnica

- **Backend:** Python, FastAPI e Pydantic v2
- **Banco:** SQLAlchemy 2.0, Alembic, PostgreSQL ou SQLite
- **Autenticação:** Google Identity Services e JWT de sessão da aplicação
- **Autorização:** filtros SQL e verificações pontuais centralizados em `app/policies.py`
- **Frontend:** HTML, CSS e JavaScript puro
- **Deploy:** função serverless Python e frontend estático na Vercel

## Estrutura do repositório

- `app/` — aplicação FastAPI, modelos, esquemas, políticas, routers e autenticação
- `frontend/` — interface HTML/CSS/JavaScript
- `api/index.py` — entrypoint ASGI da Vercel
- `migrations/` — migrações Alembic
- `tests/` — fixtures e testes pytest
- `docs/` — decisões de arquitetura e produto

Detalhes técnicos:

- [Arquitetura e decisões de segurança](docs/arq-decisoes-final.md)
- [Decisões de produto](docs/decisoes-produto.md)
