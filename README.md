# CompEdu

Aplicação web para mural interno e registros pedagógicos. O protótipo visual está em `prototipo/mockups_canva`.

As decisões e questões ainda a validar estão registradas em [docs/decisoes-produto.md](docs/decisoes-produto.md).

## Backend inicial

O backend usa FastAPI, SQLAlchemy e PostgreSQL. Se `DATABASE_URL` não estiver definida, usa SQLite local para facilitar exploração. A API documentada fica em `/docs`.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d db
```

Para uma instância descartável local, mantenha o SQLite padrão, carregue dados sintéticos e inicie o servidor:

```powershell
python -m app.seed_demo
uvicorn app.main:app --reload
```

Abra `http://127.0.0.1:8000` para o protótipo, `http://127.0.0.1:8000/docs` para explorar a API e `http://127.0.0.1:8000/api/health` para conferir o serviço. As contas, senha de demonstração e dados criados por `seed_demo` são exclusivamente fictícios. O frontend ainda usa seus dados locais em memória; os endpoints reais estão disponíveis em `/api`.

Contas locais após executar `seed_demo`:

- Administração: `admin@example.com` / `DemoAdmin2026!`
- Professora: `prof@example.com` / `DemoProf2026!`
- Coordenação: `coord@example.com` / `DemoCoord2026!`

Para um banco PostgreSQL separado, edite `.env` com uma `DATABASE_URL` e uma `SECRET_KEY` aleatória, suba o serviço `db` com `docker compose up -d db` e crie uma conta inicial com `python -m app.create_admin`. Não use as credenciais de demonstração fora do ambiente local.

## API disponível

- `POST /api/auth/login` e `GET /api/auth/me`
- Administração: `GET/POST /api/admin/users`, `POST /api/classes`, `POST /api/students`
- Consultas de turma/aluno: `GET /api/classes`, `GET /api/students`
- Registros pedagógicos: `GET/POST /api/records`
- Mural: `GET/POST /api/announcements`
- `GET /api/health`

Papéis disponíveis: `admin`, `teacher`, `coordination`, `secretary`, `support`. Cada conta e cada publicação tem nível numérico de 1 a 5. O nível 1 é o mais alto: uma pessoa vê publicações cujo nível seja igual ou numericamente maior que o dela. Por exemplo, nível 2 vê publicações dos níveis 2, 3, 4 e 5. Professores também precisam estar vinculados à turma do aluno para consultar ou registrar informações. As verificações ocorrem na API; papéis controlam ações administrativas e níveis controlam leitura.

## Próximos passos

Antes de usar dados reais, definir com a escola a matriz final de acesso, processos de criação/desativação de contas, retenção e auditoria. A primeira versão cria tabelas automaticamente; migrações de banco, anexos, recuperação de senha, edição e remoção de conteúdo ainda precisam ser implementados.
