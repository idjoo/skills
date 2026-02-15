# Provisioning Reference

Complete file templates for scaffolding a new Python FastAPI backend service. Use these exact contents when creating a new project.

## Table of Contents

- [pyproject.toml](#pyprojecttoml)
- [config.example.yaml](#configexampleyaml)
- [docker-compose.yml](#docker-composeyml)
- [flake.nix](#flakenix)
- [CI/CD](#cicd) (Dockerfile, cloud-build.yaml, skaffold.yaml, cloud-run.yaml)
- [Database](#database) (alembic.ini, env.py, script.py.mako)
- [Source Skeleton](#source-skeleton) (all src/ files)
- [Provisioning Steps](#provisioning-steps)

---

## pyproject.toml

```toml
[build-system]
build-backend = "hatchling.build"
requires = [ "hatchling" ]

[project]
name = "<service-name>"
version = "0.0.1"
description = ""
readme = "README.md"
requires-python = ">=3.13"
classifiers = [
  "Programming Language :: Python :: 3 :: Only",
  "Programming Language :: Python :: 3.13",
  "Programming Language :: Python :: 3.14",
]
dependencies = [
  "fastapi[all]>=0.115.8",
  "fastapi-pagination>=0.12.34",
  "google-cloud-logging>=3.11.4",
  "greenlet>=3.1.1",
  "opentelemetry-api>=1.30",
  "opentelemetry-exporter-gcp-logging>=1.9.0a0",
  "opentelemetry-exporter-gcp-trace>=1.9",
  "opentelemetry-propagator-gcp>=1.9",
  "opentelemetry-sdk>=1.30",
  "psycopg[binary]>=3.2.9",
  "pydantic-settings>=2.7.1",
  "sqlmodel>=0.0.22",
  "wrapt>=2.0.1",
]

scripts.app = "src:server"

[dependency-groups]
dev = [
  "alembic>=1.16.4",
  "coverage>=7.6.10",
  "pre-commit>=4.1",
  "pytest-asyncio>=0.25.3",
  "pytest-cov>=6",
  "ruff>=0.9.4",
]

[tool.hatch.build.targets.wheel]
packages = [ "src" ]

[tool.uv]
package = true

[tool.ruff]
line-length = 80

lint.extend-select = [ "ASYNC", "F", "FAST", "I", "RUF", "UP" ]
```

---

## config.example.yaml

```yaml
service: <service-name>

host: "0.0.0.0"
port: 8080

environment: local

logging:
  level: debug

database:
  # url: ""
  kind: "postgresql"
  adapter: "psycopg"
  username: "username"
  password: "password"
  host: "localhost"
  port: 5432
  name: "database"
```

---

## docker-compose.yml

```yaml
services:
  database:
    image: postgres:17-alpine
    environment:
      - POSTGRES_USER=${DATABASE_USERNAME:-username}
      - POSTGRES_PASSWORD=${DATABASE_PASSWORD:-password}
      - POSTGRES_DB=${DATABASE_NAME:-database}
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready"]
```

---

## flake.nix

```nix
{
  description = "Python";

  inputs.nixpkgs.url = "https://flakehub.com/f/NixOS/nixpkgs/0.1.0.tar.gz";

  outputs =
    { self, nixpkgs }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forEachSupportedSystem =
        f:
        nixpkgs.lib.genAttrs supportedSystems (
          system:
          f {
            pkgs = import nixpkgs { inherit system; };
          }
        );
    in
    {
      devShells = forEachSupportedSystem (
        { pkgs }:
        {
          default = pkgs.mkShell {
            venvDir = ".venv";

            packages = [
              pkgs.pre-commit
              pkgs.uv

              (pkgs.python313.withPackages (
                p: with p; [
                  venvShellHook
                  pip
                ]
              ))
            ];

            shellHook = ''
              export LD_LIBRARY_PATH=${
                pkgs.lib.makeLibraryPath [
                  pkgs.stdenv.cc.cc.lib
                  pkgs.libz
                ]
              }
              source .venv/bin/activate
            '';
          };
        }
      );
    };
}
```

---

## CI/CD

### ci/Dockerfile

```dockerfile
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

ENV UV_LINK_MODE=copy

COPY uv.lock .

COPY pyproject.toml .

RUN uv sync --frozen --no-install-project --no-editable

COPY . /app

RUN uv sync --frozen --no-editable



FROM python:3.13-slim

ENV TZ="Asia/Jakarta"
ENV PYTHONWARNINGS="ignore::UserWarning"

WORKDIR /app

RUN useradd --uid 1000 --user-group --system app \
  && chown --recursive app:app /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv

COPY --from=builder --chown=app:app /app/db /app/db

USER app

CMD ["/app/.venv/bin/app"]
```

### ci/cloud-build.yaml

```yaml
substitutions:
  _SERVICE: <service-name>
  _REGION: asia-southeast2
  _REGISTRY: docker
  _IMAGE: ${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REGISTRY}/${_SERVICE}

steps:
  - name: gcr.io/cloud-builders/gcloud
    script: |
      #!/bin/bash

      sed -i "s|{{PROJECT_ID}}|${PROJECT_ID}|g" ci/*.yaml
      sed -i "s|{{_REGION}}|${_REGION}|g" ci/*.yaml
      sed -i "s|{{_IMAGE}}|${_IMAGE}|g" ci/*.yaml
      sed -i "s|{{_SERVICE}}|${_SERVICE}|g" ci/*.yaml

  - name: gcr.io/k8s-skaffold/skaffold
    entrypoint: skaffold
    args:
      - run
      - --filename=ci/skaffold.yaml

serviceAccount: projects/${PROJECT_ID}/serviceAccounts/builder@${PROJECT_ID}.iam.gserviceaccount.com
logsBucket: ${PROJECT_ID}_cloudbuild

options:
  dynamicSubstitutions: true
  automapSubstitutions: true
```

### ci/skaffold.yaml

```yaml
apiVersion: skaffold/v4beta13
kind: Config
build:
  googleCloudBuild:
    projectId: "{{PROJECT_ID}}"
    serviceAccount: "projects/{{PROJECT_ID}}/serviceAccounts/builder@{{PROJECT_ID}}.iam.gserviceaccount.com"
  artifacts:
    - image: "{{_IMAGE}}"
      kaniko:
        dockerfile: ci/Dockerfile
        useNewRun: true
        destination:
          - "{{_IMAGE}}:latest"
deploy:
  cloudrun:
    projectid: "{{PROJECT_ID}}"
    region: "{{_REGION}}"
manifests:
  rawYaml:
    - ci/cloud-run.yaml
```

### ci/cloud-run.yaml

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: "{{_SERVICE}}"
  annotations:
    run.googleapis.com/ingress: all
    run.googleapis.com/invoker-iam-disabled: 'true'
spec:
  template:
    metadata:
      labels:
        run.googleapis.com/startupProbeType: Custom
      annotations:
        autoscaling.knative.dev/maxScale: '10'
        run.googleapis.com/startup-cpu-boost: 'true'
    spec:
      containerConcurrency: 80
      timeoutSeconds: 300
      containers:
        - name: "{{_SERVICE}}"
          image: "{{_IMAGE}}"
          ports:
            - name: http1
              containerPort: 8080
          env:
            - name: CONFIG_YAML
              value: /configs/config.yaml
          resources:
            limits:
              cpu: 1000m
              memory: 512Mi
          volumeMounts:
            - name: config
              mountPath: /configs
          livenessProbe:
            timeoutSeconds: 10
            periodSeconds: 10
            failureThreshold: 3
            httpGet:
              path: /health
              port: 8080
          startupProbe:
            timeoutSeconds: 10
            periodSeconds: 10
            failureThreshold: 3
            httpGet:
              path: /health
              port: 8080
      volumes:
        - name: config
          secret:
            secretName: "{{_SERVICE}}-config"
            items:
              - key: latest
                path: config.yaml
```

---

## Database

### db/alembic.ini

```ini
[alembic]
script_location = %(here)s
prepend_sys_path = ..
path_separator = os
sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]
hooks = ruff_check, ruff_format

ruff_check.type = module
ruff_check.module = ruff
ruff_check.options = check --fix REVISION_SCRIPT_FILENAME

ruff_format.type = module
ruff_format.module = ruff
ruff_format.options = format REVISION_SCRIPT_FILENAME

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### db/env.py

```python
import asyncio
from urllib.parse import quote

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from src.dependencies import Config, get_config

config = context.config
app_config: Config = get_config()

target_metadata = SQLModel.metadata

url = ""
if app_config.database.url:
    url = app_config.database.url
else:
    url = (
        f"{app_config.database.kind}+{app_config.database.adapter}://"
        f"{app_config.database.username}:{quote(app_config.database.password)}@"
        f"{app_config.database.host}:{app_config.database.port}/"
        f"{app_config.database.name}"
    )
config.set_main_option("sqlalchemy.url", url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### db/script.py.mako

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade schema."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade schema."""
    ${downgrades if downgrades else "pass"}
```

### db/versions/.keep

Empty file. Create with `touch db/versions/.keep`.

### db/README

```
Generic single-database configuration with an async dbapi.
```

---

## Source Skeleton

### src/\_\_init\_\_.py

```python
from .main import app, server

__all__ = ["app", "server"]
```

### src/main.py

```python
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi_pagination import add_pagination

from src.dependencies import (
    Config,
    Environment,
    Logger,
    get_config,
    get_logger,
)
from src.exceptions import BaseError
from src.routers import HealthRouter


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.dependencies import database, http_client, logger, tracer

    await database.init()
    await tracer.init()
    await logger.init()
    await http_client.init()
    yield
    await http_client.close()
    await database.close()


config: Config = get_config()
logger: Logger = get_logger()


title = "<Service Name> - Swagger UI"


app = FastAPI(
    lifespan=lifespan,
    title=title,
    contact={
        "name": "<Author>",
        "url": "https://example.com",
        "email": "author@example.com",
    },
    docs_url=None,
)


# ===============
# Middlewares
# ===============
add_pagination(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===============
# Routers
# ===============
app.include_router(HealthRouter)


# ===============
# Handlers
# ===============
@app.exception_handler(BaseError)
async def http_exception_handler(request, exception):
    logger.error(exception.message, exc_info=True)
    return JSONResponse(
        status_code=exception.status_code,
        content={
            "status_code": exception.status_code,
            "message": exception.message,
            "data": None,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exception):
    data = {}
    for error in exception.errors():
        loc, msg = error["loc"], error["msg"]
        filtered_loc = loc[1:] if loc[0] in ("body", "query", "path") else loc
        field_string = ".".join(filtered_loc)
        if field_string not in data:
            data[field_string] = []
        data[field_string].append(msg)

    return JSONResponse(
        status_code=400,
        content={
            "status_code": 400,
            "message": "Validation Error",
            "data": data,
        },
    )


# ===============
# Base Routers
# ===============
if config.environment != Environment.PRD:
    """Enable docs only for Development environment"""

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=title,
            swagger_ui_parameters=app.swagger_ui_parameters,
        )

    @app.get("/", include_in_schema=False)
    async def home():
        return RedirectResponse("/docs")


# ===============
# WSGI
# ===============
def server():
    uvicorn.run(
        app="src:app",
        host="0.0.0.0",
        port=config.port,
        log_level=config.logging.level.lower(),
        reload=True if config.environment == Environment.LOCAL else False,
    )
```

### src/dependencies/\_\_init\_\_.py

```python
from . import (
    config as config,
)
from . import (
    database as database,
)
from . import (
    http_client as http_client,
)
from . import (
    logger as logger,
)
from . import (
    tracer as tracer,
)
from .config import (
    Config as Config,
)
from .config import (
    Environment as Environment,
)
from .config import (
    get_config as get_config,
)
from .database import Database as Database
from .http_client import HttpClient as HttpClient
from .logger import (
    Logger as Logger,
)
from .logger import (
    get_logger as get_logger,
)
from .tracer import (
    observe as observe,
)
from .tracer import (
    track as track,
)
```

### src/dependencies/config.py

```python
from enum import StrEnum, auto
from os import environ
from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
    YamlConfigSettingsSource,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        nested_model_default_partial_update=True,
        json_file=environ.get("CONFIG_JSON", "config.json"),
        toml_file=environ.get("CONFIG_TOML", "config.toml"),
        yaml_file=environ.get("CONFIG_YAML", "config.yaml"),
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            JsonConfigSettingsSource(settings_cls),
            TomlConfigSettingsSource(settings_cls),
            init_settings,
        )


class Environment(StrEnum):
    LOCAL = auto()
    DEV = auto()
    PRD = auto()


class LoggingLevel(StrEnum):
    DEBUG = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()


class Logging(BaseModel):
    level: LoggingLevel = LoggingLevel.INFO


class Database(BaseModel):
    url: str | None = None
    kind: str = "postgresql"
    adapter: str = "psycopg"
    username: str = "username"
    password: str = "password"
    host: str = "localhost"
    port: int = 5432
    name: str = "database"


class BaseConfig(Settings):
    service: str
    host: str = "0.0.0.0"
    port: int = 8080
    environment: Environment = Environment.LOCAL
    logging: Logging = Logging()
    database: Database = Database()


async def aget_config() -> BaseConfig:
    return BaseConfig()


def get_config() -> BaseConfig:
    return BaseConfig()


Config = Annotated[BaseConfig, Depends(aget_config)]
```

### src/dependencies/database.py

```python
from typing import Annotated
from urllib.parse import quote

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from .config import Config, get_config
from .logger import Logger, get_logger

config: Config = get_config()
logger: Logger = get_logger()

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine

    if _engine is None:
        url = config.database.url
        if not url:
            url = (
                f"{config.database.kind}+{config.database.adapter}://"
                f"{config.database.username}:{quote(config.database.password)}@"
                f"{config.database.host}:{config.database.port}/"
                f"{config.database.name}"
            )

        logger.info(f"creating database engine: {url}")

        _engine = create_async_engine(
            url=url,
            echo=config.logging.level == "debug",
            future=True,
            pool_size=20,
            max_overflow=10,
        )

    return _engine


async def init():
    import asyncio

    from alembic import command
    from alembic.config import Config as AlembicConfig

    await asyncio.to_thread(
        command.upgrade, config=AlembicConfig("alembic.ini"), revision="head"
    )


async def close():
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


async def aget_session() -> AsyncSession:
    engine = get_engine()
    session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session() as session:
        yield session


Database = Annotated[AsyncSession, Depends(aget_session)]
```

### src/dependencies/logger.py

```python
import logging
import sys
from typing import Annotated

from fastapi import Depends
from google.cloud.logging.handlers import StructuredLogHandler
from opentelemetry import _logs
from opentelemetry.exporter.cloud_logging import (
    CloudLoggingExporter,
)
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

from .config import Config, get_config

config: Config = get_config()


async def init():
    logger_provider = LoggerProvider(
        resource=Resource.create({"service.name": config.service}),
    )

    _logs.set_logger_provider(logger_provider)

    _logs.get_logger_provider().add_log_record_processor(
        BatchLogRecordProcessor(
            CloudLoggingExporter(default_log_name=config.service),
        )
    )

    logger = logging.getLogger(config.service)
    logger.setLevel(config.logging.level.upper())
    logger.addHandler(StructuredLogHandler(stream=sys.stdout))
    logger.addHandler(LoggingHandler())


async def aget_logger() -> logging.Logger:
    return logging.getLogger(config.service)


def get_logger() -> logging.Logger:
    return logging.getLogger(config.service)


Logger = Annotated[logging.Logger, Depends(aget_logger)]
```

### src/dependencies/tracer.py

```python
import inspect
from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager, contextmanager

import wrapt
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.cloud_trace_propagator import (
    CloudTraceFormatPropagator,
)
from opentelemetry.sdk.resources import Attributes, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import SpanKind
from opentelemetry.trace.span import Span
from opentelemetry.trace.status import StatusCode

from .config import Config, aget_config, get_config


async def init():
    config: Config = await aget_config()

    tracer_provider = TracerProvider(
        resource=Resource.create({"service.name": config.service}),
    )

    trace.set_tracer_provider(tracer_provider)

    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(
            CloudTraceSpanExporter(resource_regex=r".*"),
        )
    )

    set_global_textmap(CloudTraceFormatPropagator())


@asynccontextmanager
async def track(
    name: str,
    attributes: Attributes | None = None,
) -> Iterator[Span]:
    config: Config = await aget_config()
    tracer = trace.get_tracer(config.service)

    with tracer.start_as_current_span(
        name,
        kind=SpanKind.INTERNAL,
        record_exception=True,
        set_status_on_exception=True,
        end_on_exit=True,
        attributes=attributes,
    ) as span:
        yield span
        span.set_status(StatusCode.OK)


@contextmanager
def create_span(func: Callable):
    config: Config = get_config()
    tracer = trace.get_tracer(config.service)

    with tracer.start_as_current_span(
        func.__qualname__,
        kind=SpanKind.INTERNAL,
        record_exception=True,
        set_status_on_exception=True,
        end_on_exit=True,
    ) as span:
        span.set_attribute(SpanAttributes.CODE_FUNCTION, func.__qualname__)
        span.set_attribute(SpanAttributes.CODE_NAMESPACE, func.__module__)
        span.set_attribute(SpanAttributes.CODE_FILEPATH, inspect.getfile(func))
        yield span
        span.set_status(StatusCode.OK)


@wrapt.decorator
def _observe(wrapped, instance, args, kwargs):
    if inspect.iscoroutinefunction(wrapped):

        async def _awrapper():
            with create_span(wrapped):
                return await wrapped(*args, **kwargs)

        return _awrapper()
    else:
        with create_span(wrapped):
            return wrapped(*args, **kwargs)


def observe(wrapped=None):
    if wrapped is None:
        return _observe
    return _observe(wrapped)


__all__ = ["observe", "track"]
```

### src/dependencies/http_client.py

```python
from typing import Annotated

from fastapi import Depends
from httpx import AsyncClient

_client: AsyncClient | None = None


async def init():
    global _client
    if _client is None:
        _client = AsyncClient(timeout=60)


async def close():
    global _client
    if _client:
        await _client.aclose()
        _client = None


async def aget_client() -> AsyncClient:
    global _client
    if _client is None:
        await init()
    return _client


HttpClient = Annotated[AsyncClient, Depends(aget_client)]
```

### src/exceptions/\_\_init\_\_.py

```python
from .base_exception import BaseError as BaseError
from .health_exception import (
    DatabaseHealthError as DatabaseHealthError,
)
```

### src/exceptions/base_exception.py

```python
class BaseError(Exception):
    def __init__(
        self,
        message: str = "Internal Server Error",
        status_code: int = 500,
    ):
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)
```

### src/exceptions/health_exception.py

```python
from .base_exception import BaseError


class DatabaseHealthError(BaseError):
    def __init__(self):
        super().__init__(status_code=500, message="Database Not Healthy")
```

### src/schemas/\_\_init\_\_.py

```python
from .health_schema import HealthCheck as HealthCheck
from .page_schema import Page as Page
from .response_schema import Response as Response
```

### src/schemas/health_schema.py

```python
from pydantic import BaseModel


class HealthCheck(BaseModel):
    """Response model to validate and return when performing a health check."""

    status: str = "OK"
    version: str = ""
```

### src/schemas/page_schema.py

```python
from typing import TypeVar

from fastapi import Query
from fastapi_pagination import Page as BasePage
from fastapi_pagination.customization import CustomizedPage, UseParamsFields

T = TypeVar("T")


Page = CustomizedPage[
    BasePage[T],
    UseParamsFields(
        size=Query(100, ge=1, le=500),
    ),
]
```

### src/schemas/response_schema.py

```python
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Response[T](BaseModel):
    status: int = 200
    message: str = ""
    data: T | None
```

### src/models/\_\_init\_\_.py

```python
```

Empty initially. Add model imports here as entities are created.

### src/repositories/\_\_init\_\_.py

```python
from .health_repository import HealthRepository as HealthRepository
```

### src/repositories/health_repository.py

```python
from sqlalchemy import select

from src.dependencies import Database
from src.exceptions import DatabaseHealthError


class HealthRepository:
    db: Database

    def __init__(
        self,
        db: Database,
    ) -> None:
        self.db = db

    async def check(
        self,
    ) -> bool:
        try:
            await self.db.exec(select(1))
        except Exception:
            raise DatabaseHealthError()

        return True
```

### src/services/\_\_init\_\_.py

```python
from .health_service import HealthService as HealthService
```

### src/services/health_service.py

```python
from importlib import metadata
from typing import Annotated

from fastapi import Depends

from src.dependencies import Config
from src.repositories import HealthRepository
from src.schemas import HealthCheck


class HealthService:
    config: Config
    health_repository: HealthRepository

    def __init__(
        self,
        config: Config,
        health_repository: Annotated[HealthRepository, Depends()],
    ) -> None:
        self.config = config
        self.health_repository = health_repository

    async def check(
        self,
    ) -> HealthCheck:
        health_check = HealthCheck()
        if await self.health_repository.check():
            health_check.status = "OK"
        health_check.version = metadata.version(self.config.service)
        return health_check
```

### src/routers/\_\_init\_\_.py

```python
from .health_router import HealthRouter as HealthRouter
```

### src/routers/health_router.py

```python
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.schemas import HealthCheck
from src.services import HealthService

HealthRouter = APIRouter(
    tags=["health"],
)


@HealthRouter.get(
    "/health",
    summary="Perform a Health Check",
    response_description="Return HTTP Status Code 200 (OK)",
    status_code=status.HTTP_200_OK,
)
async def health(
    health_service: Annotated[HealthService, Depends()],
) -> HealthCheck:
    """
    ## Perform a Health Check
    Endpoint to perform a healthcheck on. This endpoint can primarily be used Docker
    to ensure a robust container orchestration and management is in place. Other
    services which rely on proper functioning of the API service will not deploy if this
    endpoint returns any other HTTP status code except 200 (OK).
    Returns:
        HealthCheck: Returns a JSON response with the health status
    """
    return await health_service.check()
```

---

## Provisioning Steps

Follow these steps in order to scaffold a new service from the templates above:

1. Replace all `<service-name>` placeholders with the actual service name (in `pyproject.toml`, `config.example.yaml`, `ci/cloud-build.yaml`)
2. Replace `<Service Name>`, `<Author>`, email, and URL in `src/main.py`
3. Create all directories:
   ```bash
   mkdir -p src/{dependencies,models,schemas,exceptions,repositories,services,routers} db/versions ci
   ```
4. Write all files from the templates above
5. Create the versions keep file:
   ```bash
   touch db/versions/.keep
   ```
6. Install dependencies and generate the lock file:
   ```bash
   uv sync
   ```
7. Copy the example config:
   ```bash
   cp config.example.yaml config.yaml
   ```
8. Start the local PostgreSQL database:
   ```bash
   docker compose up -d
   ```
9. Start the service:
   ```bash
   uv run app
   ```
10. Verify the health endpoint:
    ```bash
    curl http://localhost:8080/health
    ```
