# Python FastAPI Backend Architecture Reference

Code templates for each architectural layer and cross-cutting concern. Every new feature follows these patterns.

## Table of Contents

- [Cross-Cutting Concerns](#cross-cutting-concerns)
- [Models](#models)
- [Exceptions](#exceptions)
- [Repositories](#repositories)
- [Services](#services)
- [Routers](#routers)
- [Schemas](#schemas)
- [Dependencies](#dependencies)
- [Registration Pattern](#registration-pattern)

---

## Cross-Cutting Concerns

Logger, Tracer, and Exceptions are available at **any layer**. The templates below show them used in typical positions, but they are not exclusive to those layers. Annotated with `# -- cross-cutting` comments.

**Logging** — Inject `Logger` via DI. Use structured JSON dicts:

```python
# Available at any layer via constructor injection
logger.info({"message": "Something happened", "entity_id": str(id)})
logger.debug({"message": "Detail", "data": entity.model_dump(mode="json")})
logger.warning({"message": "Potential issue", "error": str(error)})
logger.error({"message": "Failure", "error": str(error)}, exc_info=True)
```

**Tracing** — Decorate any method, add sub-spans for business logic:

```python
from src.dependencies import tracer

@tracer.observe()                                          # auto-span from method name
async def any_method(self, ...):
    async with tracer.track("logic:name", attributes={     # manual sub-span
        "key": "value",
    }) as span:
        result = ...
        span.set_attribute("result.id", str(result.id))
        return result
```

**Exceptions** — Raise domain errors from any layer. All caught by global handler in `main.py`:

```python
from src.exceptions import BaseError, <Entity>NotFoundError

# In any layer:
raise <Entity>NotFoundError()                    # domain error (404)
raise BaseError("Something went wrong")          # generic error (500)
```

---

## Models

Pattern: Base -> Table -> Create -> Public -> Update

```python
from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class <Entity>Base(SQLModel):
    name: str = Field()
    # ... domain fields


class <Entity>(<Entity>Base, table=True):
    __tablename__: str = "<entities>"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column_kwargs={"onupdate": datetime.now},
    )


class <Entity>Create(<Entity>Base):
    pass


class <Entity>Public(<Entity>Base):
    id: UUID


class <Entity>Update(<Entity>Base):
    name: str | None = None
    # ... all fields optional
```

---

## Exceptions

Pattern: Domain errors extend BaseError with fixed status_code and message.

BaseError:

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

Domain errors:

```python
from .base_exception import BaseError


class <Entity>NotFoundError(BaseError):
    def __init__(self):
        super().__init__(status_code=404, message="<Entity> Not Found")


class <Entity>AlreadyExistsError(BaseError):
    def __init__(self):
        super().__init__(status_code=409, message="<Entity> Already Exists")
```

---

## Repositories

**Core responsibility:** Data access using `Database` (AsyncSession). Translates DB exceptions into domain exceptions.

```python
from uuid import UUID

from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlmodel import delete, insert, select, update

from src.dependencies import Database, Logger, tracer         # -- cross-cutting
from src.exceptions import (
    BaseError,
    <Entity>AlreadyExistsError,
    <Entity>NotFoundError,
)
from src.models import (
    <Entity>,
    <Entity>Create,
    <Entity>Update,
)
from src.schemas import Page


class <Entity>Repository:
    db: Database
    logger: Logger                                             # -- cross-cutting

    def __init__(self, db: Database, logger: Logger) -> None:  # -- cross-cutting: logger
        self.db = db
        self.logger = logger

    @tracer.observe()                                          # -- cross-cutting
    async def create(self, entity: <Entity>Create) -> <Entity>:
        try:
            data = <Entity>.model_validate(entity)
            result = (
                await self.db.scalars(
                    insert(<Entity>).values(data.model_dump()).returning(<Entity>),
                )
            ).one()
            await self.db.commit()
            self.logger.debug({"message": "<Entity> created in DB", "<entity>": result.model_dump(mode="json")})  # -- cross-cutting
            return result
        except IntegrityError as error:
            self.logger.warning({"message": "<Entity> creation failed: already exists", "error": str(error)})  # -- cross-cutting
            raise <Entity>AlreadyExistsError() from error
        except Exception as error:
            self.logger.error({"message": "Database error during creation", "error": str(error)}, exc_info=True)  # -- cross-cutting
            raise BaseError("Database Internal Error") from error

    @tracer.observe()                                          # -- cross-cutting
    async def read_all(self) -> Page[<Entity>]:
        try:
            return await paginate(self.db, select(<Entity>))
        except Exception as error:
            self.logger.error({"message": "Database error during read_all", "error": str(error)}, exc_info=True)  # -- cross-cutting
            raise BaseError("Database Internal Error") from error

    @tracer.observe()                                          # -- cross-cutting
    async def read(self, id: UUID) -> <Entity> | None:
        try:
            result = (await self.db.exec(select(<Entity>).where(<Entity>.id == id))).one()
            return result
        except NoResultFound as error:
            self.logger.warning({"message": "<Entity> not found", "<entity>_id": str(id)})  # -- cross-cutting
            raise <Entity>NotFoundError() from error
        except Exception as error:
            self.logger.error({"message": "Database error during read", "error": str(error)}, exc_info=True)  # -- cross-cutting
            raise BaseError("Database Internal Error") from error

    @tracer.observe()                                          # -- cross-cutting
    async def update(self, id: UUID, entity: <Entity>Update) -> <Entity>:
        try:
            result = (
                await self.db.scalars(
                    update(<Entity>)
                    .where(<Entity>.id == id)
                    .values(entity.model_dump(mode="json", exclude_none=True))
                    .returning(<Entity>),
                )
            ).one()
            await self.db.commit()
            self.logger.debug({"message": "<Entity> updated in DB", "<entity>": result.model_dump(mode="json")})  # -- cross-cutting
            return result
        except Exception as error:
            self.logger.error({"message": "Database error during update", "error": str(error)}, exc_info=True)  # -- cross-cutting
            raise BaseError("Database Internal Error") from error

    @tracer.observe()                                          # -- cross-cutting
    async def delete(self, id: UUID) -> None:
        try:
            await self.db.exec(delete(<Entity>).where(<Entity>.id == id))
            await self.db.commit()
            self.logger.debug({"message": "<Entity> deleted from DB", "<entity>_id": str(id)})  # -- cross-cutting
        except Exception as error:
            self.logger.error({"message": "Database error during delete", "error": str(error)}, exc_info=True)  # -- cross-cutting
            raise BaseError("Database Internal Error") from error
```

---

## Services

**Core responsibility:** Business logic and orchestration. Delegates data access to repository via `Annotated[Repository, Depends()]`.

```python
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from src.dependencies import Logger, tracer                    # -- cross-cutting
from src.models import <Entity>, <Entity>Create, <Entity>Update
from src.repositories import <Entity>Repository
from src.schemas import Page


class <Entity>Service:
    <entity>_repository: <Entity>Repository
    logger: Logger                                             # -- cross-cutting

    def __init__(
        self,
        <entity>_repository: Annotated[<Entity>Repository, Depends()],
        logger: Logger,                                        # -- cross-cutting
    ) -> None:
        self.<entity>_repository = <entity>_repository
        self.logger = logger

    @tracer.observe()                                          # -- cross-cutting
    async def create(self, entity: <Entity>Create) -> <Entity>:
        async with tracer.track("logic:create_<entity>", attributes={"<entity>.name": entity.name}) as span:  # -- cross-cutting
            try:
                self.logger.info({"message": "Starting <entity> creation logic", "<entity>": entity.model_dump(mode="json")})  # -- cross-cutting
                result = await self.<entity>_repository.create(entity)
                span.set_attribute("<entity>.id", str(result.id))  # -- cross-cutting
                return result
            except Exception as e:
                self.logger.error({"message": "Failed to create <entity> in logic layer", "error": str(e)})  # -- cross-cutting
                span.record_exception(e)                       # -- cross-cutting
                raise

    @tracer.observe()                                          # -- cross-cutting
    async def read_all(self) -> Page[<Entity>]:
        async with tracer.track("logic:read_all_<entities>") as span:  # -- cross-cutting
            self.logger.debug({"message": "Fetching all <entities> from repository"})  # -- cross-cutting
            result = await self.<entity>_repository.read_all()
            span.set_attribute("<entities>.count", len(result.items))  # -- cross-cutting
            return result

    @tracer.observe()                                          # -- cross-cutting
    async def read(self, id: UUID) -> <Entity> | None:
        self.logger.debug({"message": "Calling repository to read <entity>", "<entity>_id": str(id)})  # -- cross-cutting
        return await self.<entity>_repository.read(id=id)

    @tracer.observe()                                          # -- cross-cutting
    async def update(self, id: UUID, entity: <Entity>Update) -> <Entity>:
        self.logger.debug({"message": "Calling repository to update <entity>", "<entity>_id": str(id), "update_data": entity.model_dump(mode="json", exclude_none=True)})  # -- cross-cutting
        return await self.<entity>_repository.update(id, entity)

    @tracer.observe()                                          # -- cross-cutting
    async def delete(self, id: UUID) -> None:
        self.logger.debug({"message": "Calling repository to delete <entity>", "<entity>_id": str(id)})  # -- cross-cutting
        return await self.<entity>_repository.delete(id=id)
```

---

## Routers

**Core responsibility:** HTTP handling. Maps requests to service calls, wraps responses in `Response[T]` or `Page[T]`.

```python
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.dependencies import Logger, tracer                    # -- cross-cutting
from src.models import <Entity>Create, <Entity>Public, <Entity>Update
from src.schemas import Page, Response
from src.services import <Entity>Service

<Entity>Router = APIRouter(
    prefix="/<entities>",
    tags=["<entity>"],
)


@<Entity>Router.post("/")
@tracer.observe()                                              # -- cross-cutting
async def create(
    logger: Logger,                                            # -- cross-cutting
    <entity>_service: Annotated[<Entity>Service, Depends()],
    entity: <Entity>Create,
) -> Response[<Entity>Public]:
    logger.info({"message": "Creating a new <entity>", "<entity>": entity.model_dump(mode="json")})  # -- cross-cutting
    data = await <entity>_service.create(entity)
    logger.info({"message": "<Entity> created successfully", "<entity>": data.model_dump(mode="json")})  # -- cross-cutting
    return Response(status=status.HTTP_200_OK, message="<Entity> created successfully", data=data)


@<Entity>Router.get("/")
@tracer.observe()                                              # -- cross-cutting
async def read_all(
    logger: Logger,                                            # -- cross-cutting
    <entity>_service: Annotated[<Entity>Service, Depends()],
) -> Page[<Entity>Public]:
    logger.info({"message": "Reading all <entities>"})         # -- cross-cutting
    return await <entity>_service.read_all()


@<Entity>Router.get("/{id}")
@tracer.observe()                                              # -- cross-cutting
async def read(
    logger: Logger,                                            # -- cross-cutting
    <entity>_service: Annotated[<Entity>Service, Depends()],
    id: UUID,
) -> Response[<Entity>Public]:
    logger.info({"message": "Reading <entity> by ID", "<entity>_id": str(id)})  # -- cross-cutting
    data = await <entity>_service.read(id)
    return Response(status=status.HTTP_200_OK, message="Success", data=data)


@<Entity>Router.patch("/{id}")
@tracer.observe()                                              # -- cross-cutting
async def update(
    logger: Logger,                                            # -- cross-cutting
    <entity>_service: Annotated[<Entity>Service, Depends()],
    id: UUID,
    entity: <Entity>Update,
) -> Response[<Entity>Public]:
    logger.info({"message": "Updating <entity>", "<entity>_id": str(id), "update_data": entity.model_dump(exclude_none=True)})  # -- cross-cutting
    data = await <entity>_service.update(id, entity)
    logger.info({"message": "<Entity> updated successfully", "<entity>": data.model_dump(mode="json")})  # -- cross-cutting
    return Response(status=status.HTTP_200_OK, message="Successfully updated", data=data)


@<Entity>Router.delete("/{id}")
@tracer.observe()                                              # -- cross-cutting
async def delete(
    logger: Logger,                                            # -- cross-cutting
    <entity>_service: Annotated[<Entity>Service, Depends()],
    id: UUID,
) -> Response:
    logger.info({"message": "Deleting <entity>", "<entity>_id": str(id)})  # -- cross-cutting
    await <entity>_service.delete(id)
    logger.info({"message": "<Entity> deleted successfully", "<entity>_id": str(id)})  # -- cross-cutting
    return Response(status=status.HTTP_200_OK, message="Successfully deleted", data=None)
```

---

## Schemas

Response envelope:

```python
from typing import TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class Response[T](BaseModel):
    status: int = 200
    message: str = ""
    data: T | None
```

Pagination:

```python
from typing import TypeVar
from fastapi import Query
from fastapi_pagination import Page as BasePage
from fastapi_pagination.customization import CustomizedPage, UseParamsFields

T = TypeVar("T")

Page = CustomizedPage[
    BasePage[T],
    UseParamsFields(size=Query(100, ge=1, le=500)),
]
```

Health check:

```python
from pydantic import BaseModel

class HealthCheck(BaseModel):
    status: str = "OK"
    version: str = ""
```

---

## Dependencies

All dependencies follow the singleton pattern using `Annotated[T, Depends(getter)]`:

- `Config = Annotated[BaseConfig, Depends(aget_config)]` -- Multi-source YAML/JSON/TOML/env config
- `Database = Annotated[AsyncSession, Depends(aget_session)]` -- Async SQLModel session with yield
- `Logger = Annotated[logging.Logger, Depends(aget_logger)]` -- Structured GCP Cloud Logging
- `HttpClient = Annotated[AsyncClient, Depends(aget_client)]` -- Shared httpx async client

---

## Registration Pattern

Every layer package has an `__init__.py` that re-exports its public symbols using explicit `as` re-exports:

```python
# src/models/__init__.py
from .product_model import Product as Product
from .product_model import ProductCreate as ProductCreate
from .product_model import ProductPublic as ProductPublic
from .product_model import ProductUpdate as ProductUpdate
```

Same pattern for exceptions, repositories, services, routers, and schemas. This ensures clean imports throughout the codebase:

```python
# Usage in other modules:
from src.models import Product, ProductCreate
from src.exceptions import ProductNotFoundError
from src.repositories import ProductRepository
from src.services import ProductService
from src.routers import ProductRouter
```

After creating all files, register the router in `src/main.py`:

```python
from src.routers import ProductRouter

app.include_router(ProductRouter)
```
