"""Health check. Verifica a API e a conectividade com o banco."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.infrastructure.db.session import get_engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, Any]:
    settings = get_settings()
    database_ok = True
    database_error: str | None = None
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - depende de infraestrutura externa
        database_ok = False
        database_error = str(exc)

    return {
        "status": "ok" if database_ok else "degraded",
        "app": settings.app_name,
        "environment": settings.environment,
        "database": {"connected": database_ok, "error": database_error},
        "ai_available": settings.ai_enabled,
    }
