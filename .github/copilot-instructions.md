# CompEdu project instructions

* Treat `docs/arq-decisoes-final.md` and `docs/decisoes-produto.md` as the source of truth for authorization and product behavior.
* Use FastAPI with SQLAlchemy 2.0, Pydantic v2, and Alembic. Preserve the existing typed `Mapped[...]` models and UUID primary keys.
* Put HTTP handlers in `app/routers/`, shared request/response contracts in `app/schemas.py`, ORM entities in `app/models.py`, and SQL/result formatting helpers in `app/serializers.py` or the existing module responsible for that concern.
* Keep authorization out of individual routers. Reuse `app/policies.py` `scope_*` functions for SQL visibility and `ensure_*` functions for point checks.
* Preserve the two authorization axes: access levels are numeric 1..5 (1 is highest), and horizontal access depends on role, academic year, class, enrollment, and teaching assignment.
* Never weaken an existing scope to make a test pass. For missing resources or invisible resources, preserve the established 404-versus-403 behavior and do not leak hidden resource existence.
* Use `app/deps.CurrentUser`, `Db`, and role dependencies such as `AdminUser` and `EnrollmentManager` for authenticated endpoints. Keep authentication and bearer handling in `app/deps.py` and `app/security.py`.
* Validate data at Pydantic boundaries and use existing enums and constraints. Commit state changes only after audit entries that belong in the same transaction.
* Use logical deletion for pedagogical records and announcements; preserve audit history and never copy pedagogical content into audit details.
* Keep active-year and enrollment behavior consistent: a professor's default scope is the active year and current teaching assignments/enrollments, unless the policy intentionally includes authored history.
* Update `app/models.py` and create a real Alembic revision in `migrations/versions/` for schema changes. Keep migrations portable between SQLite and PostgreSQL and preserve the existing batch-alter and constraint patterns.
* Keep the frontend as a static HTML/CSS/vanilla JavaScript application. Route API calls through `frontend/api.js`; do not introduce a frontend framework or change the `/api` contract without updating both sides.
* Preserve Vercel deployment behavior: `app/main.py` remains the ASGI application, `api/index.py` exports it as `app`, and `vercel.json` continues to route `/api/*` to the serverless entrypoint.
* Read configuration only through `app/config.py` and `Settings`; do not hard-code secrets, database URLs, OAuth client IDs, or production credentials.
* Add or update pytest coverage for behavior changes, especially role and access-level matrix cases, in `tests/`. Reuse fixtures from `tests/conftest.py`.
* Run focused tests with `python -m pytest <test-file>`, or the full suite with `python -m pytest -q`. The CI command is `pytest -q` under Python 3.12.
* For database setup or migrations, use `python -m app.migrate`; use `python -m app.seed_demo` only for local development data. Do not add generated `.db`, `.pyc`, cache, `.venv`, or `.vercel` files to source control.
