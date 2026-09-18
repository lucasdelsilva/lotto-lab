"""Handler global que converte qualquer falha em ProblemDetails (RFC 7807)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import DomainError
from app.core.logging import request_id_var

logger = logging.getLogger(__name__)

PROBLEM_CONTENT_TYPE = "application/problem+json"


def problem(
    *,
    status: int,
    title: str,
    detail: str,
    code: str,
    instance: str,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"https://lotto-lab.local/errors/{code}",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
        "instance": instance,
        "request_id": request_id_var.get(),
    }
    if extra:
        body.update(extra)
    return JSONResponse(status_code=status, content=body, media_type=PROBLEM_CONTENT_TYPE)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError) -> JSONResponse:
        logger.warning("domain.error", extra={"code": exc.code, "detail": exc.detail})
        return problem(
            status=exc.status_code,
            title=exc.title,
            detail=exc.detail,
            code=exc.code,
            instance=str(request.url.path),
            extra=exc.extra,
        )

    @app.exception_handler(RequestValidationError)
    async def _request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return problem(
            status=422,
            title="Requisicao invalida",
            detail="Um ou mais campos da requisicao nao passaram na validacao.",
            code="request_validation_error",
            instance=str(request.url.path),
            extra={"errors": exc.errors()},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return problem(
            status=exc.status_code,
            title="Erro HTTP",
            detail=str(exc.detail),
            code="http_error",
            instance=str(request.url.path),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled.error")
        return problem(
            status=500,
            title="Erro interno",
            detail="Falha inesperada ao processar a requisicao.",
            code="internal_error",
            instance=str(request.url.path),
        )
