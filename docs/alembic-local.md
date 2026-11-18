# Local Alembic Workflow

Alembic manages database schema changes such as tables, columns, indexes, constraints, and relationships. Its purpose is to keep the SQLAlchemy models and the database schema evolving together without recreating the database after every change.

## Standard Development Workflow

1. Update the SQLAlchemy models in the backend.
2. Generate a new migration.
3. Review the generated file in `ticketing-backend/alembic/versions/`.
4. Apply the migration to a local database.
5. Run `alembic check` and the backend tests.
6. Commit both the application change and its migration.

## Inspecting Migrations with Docker

Run these commands from the repository root while the portfolio stack is running.

Show the currently applied revision:

```powershell
docker compose -f infra/docker-compose.yml exec ticketing-backend alembic current
```

Show migration history:

```powershell
docker compose -f infra/docker-compose.yml exec ticketing-backend alembic history
```

Apply every pending migration:

```powershell
docker compose -f infra/docker-compose.yml exec ticketing-backend alembic upgrade head
```

Revert the latest migration:

```powershell
docker compose -f infra/docker-compose.yml exec ticketing-backend alembic downgrade -1
```

Revert all migrations:

```powershell
docker compose -f infra/docker-compose.yml exec ticketing-backend alembic downgrade base
```

Mark the current schema as migrated without running migration operations:

```powershell
docker compose -f infra/docker-compose.yml exec ticketing-backend alembic stamp head
```

Use `stamp head` only when the database already matches the current models exactly. Use `alembic upgrade head` for an empty database.

## Generating a Migration

The portfolio Compose stack uses immutable application images, so migrations generated inside a running container are not written back to the host repository. Generate new migration files from a local Python environment instead:

```powershell
Set-Location ticketing-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
$env:ALEMBIC_DATABASE_URL="postgresql://ticketing:ticketing@localhost:5432/ticketing"
alembic revision --autogenerate -m "describe the schema change"
```

Review the generated migration before applying it. Alembic detects structural differences, but it cannot infer business intent or safely design every data transformation.

## Empty Database Setup

The backend does not create tables directly at startup. The Compose startup command applies migrations before starting the API:

```powershell
docker compose -f infra/docker-compose.yml up -d --build
```

To apply migrations manually in an already running stack:

```powershell
docker compose -f infra/docker-compose.yml exec ticketing-backend alembic upgrade head
```

## Test Database

The isolated backend test stack creates a temporary PostgreSQL database, applies all migrations, runs `alembic check`, and executes Pytest:

```powershell
docker compose -p ticketing-demo-test -f infra/docker-compose.test.yml up --abort-on-container-exit --exit-code-from backend-test
docker compose -p ticketing-demo-test -f infra/docker-compose.test.yml down -v
```

`ALEMBIC_DATABASE_URL` can target a specific database without changing the normal application connection:

```powershell
$env:ALEMBIC_DATABASE_URL="postgresql://ticketing:ticketing@localhost:5432/ticketing_test"
alembic upgrade head
```

## Production Guidance

A production deployment should:

1. Back up the database before high-risk schema changes.
2. Deploy application code and migration files together.
3. Run `alembic upgrade head` once from a dedicated release task or job.
4. Start application replicas only after the migration succeeds.

Do not run migrations independently from every backend replica. Destructive operations such as dropping columns or rewriting data require an explicit rollback and backup strategy.

## Important Rules

- Always review migrations generated with `--autogenerate`.
- Keep schema changes and their migration files in the same commit.
- Treat renames and data movement as manual migration work.
- Run `alembic check` in CI to detect model changes without migrations.
- Do not use `Base.metadata.create_all` as a production migration mechanism.
