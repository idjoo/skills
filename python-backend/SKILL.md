---
name: python-backend
description: "Production-ready Python backend service architecture using FastAPI, SQLModel, and async PostgreSQL. Use when: (1) Scaffolding a new backend service or API project, (2) Adding new entities, endpoints, or features to an existing service, (3) Setting up database models, migrations, or repositories, (4) Configuring CI/CD, Docker, or Cloud Run deployment, (5) Reviewing or refactoring backend code for pattern compliance. Triggers on: 'create a new service', 'add an endpoint', 'add a new entity', 'scaffold a project', 'set up a FastAPI project', 'add CRUD', 'create a model', or any Python backend development task."
---

# Python Backend

Production Python backend services with FastAPI, SQLModel, async PostgreSQL, and GCP Cloud Run deployment.

## Core Architecture

The non-negotiable pattern is the **layered flow**. Each layer only calls the layer directly below it — never skip layers.

```
Router → Service → Repository → Database
```

| Layer | Responsibility | Constraint |
|-------|---------------|------------|
| **Router** | HTTP in/out, request validation, response mapping | No business logic, no direct DB access |
| **Service** | Business logic, orchestration | No SQLModel queries, no AsyncSession, no HTTP concerns |
| **Repository** | Data access, query building, ORM operations | No business logic, no HTTP-aware errors |

Supporting constructs (not layers):

| Construct | Purpose |
|-----------|---------|
| **Model** | SQLModel table + DTOs (Create/Public/Update) |
| **Schema** | Response envelope (`Response[T]`), pagination (`Page[T]`) |
| **Dependency** | Singletons via `Annotated[T, Depends()]`: Config, Database, Logger, HttpClient |

### Cross-Cutting Concerns

Logger, Tracer, and Exceptions are **not tied to any specific layer** — use them at any layer as appropriate:

- **Logging** — `Logger` injected via DI. Structured JSON: `logger.info({"message": "...", "key": "value"})`
- **Tracing** — `@tracer.observe()` decorator on any method. `async with tracer.track("name", attributes={...})` for sub-spans
- **Exceptions** — Domain errors extend `BaseError(message, status_code)`. Raise from any layer; caught by global handler in `main.py`

## Project Structure

```
<service>/
├── pyproject.toml              # uv/hatch config, dependencies, scripts
├── config.example.yaml         # Configuration template
├── docker-compose.yml          # Local PostgreSQL
├── flake.nix                   # Nix dev shell (Python 3.13, uv, pre-commit)
├── uv.lock                     # Locked dependencies
├── ci/                         # Dockerfile, Cloud Build, Cloud Run, Skaffold
├── db/                         # Alembic migrations (async, ruff hooks)
└── src/
    ├── __init__.py              # Exports app, server
    ├── main.py                  # FastAPI app, lifespan, middleware, exception handlers
    ├── dependencies/            # Singletons: Config, Database, Logger, Tracer, HttpClient
    ├── models/                  # SQLModel table + DTO classes
    ├── schemas/                 # Response envelope, pagination, health check
    ├── exceptions/              # BaseError hierarchy
    ├── repositories/            # Data access layer
    ├── services/                # Business logic layer
    └── routers/                 # HTTP layer
```

## Workflows

### Provisioning a New Service

See [references/provisioning.md](references/provisioning.md) for complete file templates.

1. Create project directory with `pyproject.toml`, `config.example.yaml`, `docker-compose.yml`
2. Set up `flake.nix` for Nix dev shell
3. Scaffold `src/` with `__init__.py`, `main.py`, and all layer directories
4. Set up `db/` with Alembic (async env.py, sqlmodel mako template)
5. Set up `ci/` with Dockerfile, Cloud Build, Cloud Run, Skaffold
6. Run `uv sync`, copy `config.example.yaml` → `config.yaml`, start DB, run `uv run app`

### Adding a New Entity

Most common workflow. See [references/architecture.md](references/architecture.md) for code templates.

Create files in this order:

1. **Model** — `src/models/<entity>_model.py`
   - `<Entity>Base(SQLModel)` → `<Entity>(Base, table=True)` → `<Entity>Create` → `<Entity>Public` → `<Entity>Update`

2. **Exception** — `src/exceptions/<entity>_exception.py`
   - `<Entity>NotFoundError(BaseError)` (404), `<Entity>AlreadyExistsError(BaseError)` (409)

3. **Repository** — `src/repositories/<entity>_repository.py`
   - CRUD methods using `Database` (AsyncSession) via constructor injection
   - Catches `IntegrityError` → domain exception, `NoResultFound` → not found

4. **Service** — `src/services/<entity>_service.py`
   - Delegates to repository via `Annotated[Repository, Depends()]`
   - Contains business logic — not in router or repository

5. **Router** — `src/routers/<entity>_router.py`
   - `APIRouter(prefix="/<entities>", tags=["<entity>"])`
   - Endpoints: `POST /`, `GET /`, `GET /{id}`, `PATCH /{id}`, `DELETE /{id}`
   - Returns `Response[<Entity>Public]` or `Page[<Entity>Public]`

6. **Register** — Update `__init__.py` in each layer package, add router to `main.py`

7. **Migration** — `cd db && uv run alembic revision --autogenerate -m "add <entity>"`

## Key Patterns

### Dependency Injection
- Singletons: `Annotated[T, Depends(getter)]` (Config, Database, Logger, HttpClient)
- Classes: `Annotated[T, Depends()]` (Services, Repositories — no-arg Depends triggers constructor DI)

### Response Format
- Single: `Response[T]` — `{"status": 200, "message": "...", "data": {...}}`
- Paginated: `Page[T]` — fastapi-pagination, size default 100, max 500
- Error: `{"status_code": N, "message": "...", "data": null}`

### Configuration
- Multi-source: env vars → `.env` → YAML → JSON → TOML → defaults
- Nested: `env_nested_delimiter="__"` (e.g., `DATABASE__HOST=localhost`)

### Tooling
- **uv** + hatchling, Python ≥3.13, ruff (line-length=80, ASYNC/F/FAST/I/RUF/UP)
- Entry point: `scripts.app = "src:server"`
- Swagger UI at `/docs` (non-PRD only), health at `GET /health`
