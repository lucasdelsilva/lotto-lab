"""Fixtures dos testes de integracao.

Rodam contra um Postgres real, porque o import depende de ARRAY, JSONB e de uma transacao
de verdade. Sem banco alcancavel os testes sao pulados com a instrucao de como subir.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_ADMIN_URL = "postgresql+psycopg://lotto:lotto@localhost:5432/postgres"
DEFAULT_TEST_URL = "postgresql+psycopg://lotto:lotto@localhost:5432/lottolab_test"

ADMIN_URL = os.getenv("TEST_ADMIN_DATABASE_URL", DEFAULT_ADMIN_URL)
TEST_URL = os.getenv("TEST_DATABASE_URL", DEFAULT_TEST_URL)

TABLES = (
    "bet_result",
    "bet",
    "game",
    "game_batch",
    "analysis_snapshot",
    "draw",
    "import_batch",
    "modality_config",
)


def _database_available() -> bool:
    try:
        engine = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
    except Exception:
        return False
    return True


@pytest.fixture(scope="session")
def database_url() -> str:
    if not _database_available():
        pytest.skip(
            "Postgres nao alcancavel. Suba o banco com: docker compose up -d db",
            allow_module_level=True,
        )

    admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    name = TEST_URL.rsplit("/", 1)[-1]
    with admin.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
        ).first()
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
    admin.dispose()

    os.environ["DATABASE_URL"] = TEST_URL

    from app.core.config import get_settings
    from app.infrastructure.db.session import get_engine, get_session_factory

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    # A migration do Alembic e quem cria o esquema, para que ela tambem seja exercitada.
    from alembic.config import Config

    from alembic import command

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_URL)
    command.upgrade(config, "head")

    return TEST_URL


@pytest.fixture
def session(database_url: str) -> Iterator[Session]:
    engine = create_engine(database_url, future=True)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as db:
        db.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
        db.commit()
        yield db
    engine.dispose()
