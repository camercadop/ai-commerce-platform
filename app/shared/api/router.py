import uuid
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session


def _default_create_fn(body: Any, db: Session, context: dict[str, Any]) -> Any:
    raise NotImplementedError  # pragma: no cover


def _default_get_fn(
    resource_id: uuid.UUID, db: Session, context: dict[str, Any]
) -> Any:
    raise NotImplementedError  # pragma: no cover


def _default_update_fn(
    resource_id: uuid.UUID, data: dict[str, Any], db: Session, context: dict[str, Any]
) -> Any:
    raise NotImplementedError  # pragma: no cover


def _default_delete_fn(
    resource_id: uuid.UUID, db: Session, context: dict[str, Any]
) -> None:
    raise NotImplementedError  # pragma: no cover


def CRUDRouter[M, CreateSchema: BaseModel, UpdateSchema: BaseModel](
    prefix: str,
    response_model: type[Any],
    create_schema: type[CreateSchema],
    update_schema: type[UpdateSchema],
    get_db_dep: Callable[..., Session],
    service: Any = None,
    to_response: Callable[[M], Any] | None = None,
    create_fn: Callable[..., Any] = _default_create_fn,
    get_fn: Callable[..., Any] = _default_get_fn,
    update_fn: Callable[..., Any] = _default_update_fn,
    delete_fn: Callable[..., Any] = _default_delete_fn,
) -> APIRouter:
    """Build an APIRouter with create, get, update, and delete endpoints.

    Generates standard CRUD routes for a flat resource. Operation callables
    receive the request body (or resource_id), a db Session, and a context dict,
    and return a model instance. The context dict always contains a 'request' key
    with the raw FastAPI Request object, giving callables access to path params,
    query params, and headers. Use a RequestContext subclass to coerce and validate
    values from context['request'] with full Pydantic type safety.

    Args:
        prefix: URL prefix for all routes (e.g. '/api/v1/customers').
        response_model: Pydantic response schema used for serialization.
        to_response: Callable that maps a model instance to a response schema.
        create_schema: Pydantic schema for POST request bodies.
        update_schema: Pydantic schema for PATCH request bodies.
        get_db_dep: FastAPI dependency that yields a database Session.
        service: Optional service factory callable(db) -> service instance. When
            provided, default callables delegate to service.create/get/update/delete.
        create_fn: Callable(body, db, context) -> M. Called on POST.
        get_fn: Callable(resource_id, db, context) -> M. Called on GET /{id}.
        update_fn: Callable(resource_id, data, db, context) -> M. Called on PATCH /{id}.
        delete_fn: Callable(resource_id, db, context) -> None. Called on DELETE /{id}.

    Returns:
        A fully wired APIRouter with POST, GET /{id}, PATCH /{id}, DELETE /{id}.
    """
    if service is not None:
        if create_fn is _default_create_fn:
            create_fn = lambda body, db, context: service(db).create(  # noqa: E731
                **body.model_dump(), **context.get("path_params", {})
            )
        if get_fn is _default_get_fn:
            get_fn = lambda resource_id, db, context: service(db).get(  # noqa: E731
                resource_id
            )
        if update_fn is _default_update_fn:
            update_fn = lambda resource_id, data, db, context: service(db).update(  # noqa: E731
                resource_id, data
            )
        if delete_fn is _default_delete_fn:
            delete_fn = lambda resource_id, db, context: service(db).delete(  # noqa: E731
                resource_id
            )

    if to_response is None:
        to_response = lambda result: response_model.model_validate(  # noqa: E731
            result, from_attributes=True
        )

    router = APIRouter()
    db_dep = Annotated[Session, Depends(get_db_dep)]

    def _build_context(request: Request) -> dict[str, Any]:
        return {"request": request}

    def _make_create(schema: type[Any]) -> Any:
        def create_entity(request: Request, body: Any, db: Any) -> Any:
            """Create a new resource."""
            result = to_response(create_fn(body, db, _build_context(request)))
            db.commit()
            return result

        create_entity.__annotations__["body"] = schema
        create_entity.__annotations__["db"] = db_dep
        return create_entity

    def _make_update(schema: type[Any]) -> Any:
        def update_entity(
            request: Request, resource_id: uuid.UUID, body: Any, db: Any
        ) -> Any:
            """Partially update the resource with the given id."""
            result = to_response(
                update_fn(
                    resource_id,
                    body.model_dump(exclude_unset=True),
                    db,
                    _build_context(request),
                )
            )
            db.commit()
            return result

        update_entity.__annotations__["body"] = schema
        update_entity.__annotations__["db"] = db_dep
        return update_entity

    router.add_api_route(
        prefix,
        _make_create(create_schema),
        methods=["POST"],
        response_model=response_model,
        status_code=201,
    )

    @router.get(f"{prefix}/{{resource_id}}", response_model=response_model)
    def get_entity(request: Request, resource_id: uuid.UUID, db: db_dep) -> Any:
        """Return the resource with the given id."""
        return to_response(get_fn(resource_id, db, _build_context(request)))

    router.add_api_route(
        f"{prefix}/{{resource_id}}",
        _make_update(update_schema),
        methods=["PATCH"],
        response_model=response_model,
    )

    @router.delete(f"{prefix}/{{resource_id}}", status_code=204)
    def delete_entity(request: Request, resource_id: uuid.UUID, db: db_dep) -> None:
        """Delete the resource with the given id."""
        delete_fn(resource_id, db, _build_context(request))
        db.commit()

    return router
