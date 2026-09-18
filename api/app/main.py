"""Ponto de entrada da API."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.exception_handler import register_exception_handlers
from app.core.logging import configure_logging, new_request_id, request_id_var
from app.interfaces.http.routers import analysis, bets, draws, games, health, pricing

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "Analise estatistica e geracao de jogos para as loterias da Caixa. "
            "A geracao e deterministica e reprodutivel pela seed."
        ),
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        token = request_id_var.set(request.headers.get("x-request-id") or new_request_id())
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "http.request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
        response.headers["x-request-id"] = request_id_var.get()
        request_id_var.reset(token)
        return response

    register_exception_handlers(app)

    app.include_router(health.router, prefix="/api")
    app.include_router(pricing.router, prefix="/api")
    app.include_router(draws.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")
    app.include_router(games.router, prefix="/api")
    app.include_router(bets.router, prefix="/api")

    return app


app = create_app()
