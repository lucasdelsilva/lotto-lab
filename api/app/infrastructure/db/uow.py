"""Unit of Work. Uma transacao explicita por caso de uso que escreve no banco."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.session import get_session_factory
from app.infrastructure.repositories.bet_repository import BetRepository
from app.infrastructure.repositories.draw_repository import DrawRepository
from app.infrastructure.repositories.game_repository import GameRepository
from app.infrastructure.repositories.snapshot_repository import SnapshotRepository


class UnitOfWork:
    """Agrupa os repositorios sob uma unica sessao e um unico commit."""

    session: Session
    draws: DrawRepository
    games: GameRepository
    bets: BetRepository
    snapshots: SnapshotRepository

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._session_factory = session_factory or get_session_factory()
        self._owns_session = True

    @classmethod
    def from_session(cls, session: Session) -> UnitOfWork:
        """Reaproveita a sessao da requisicao, sem abrir outra conexao."""
        uow = cls.__new__(cls)
        uow._session_factory = None  # type: ignore[assignment]
        uow._owns_session = False
        uow._bind(session)
        return uow

    def _bind(self, session: Session) -> None:
        self.session = session
        self.draws = DrawRepository(session)
        self.games = GameRepository(session)
        self.bets = BetRepository(session)
        self.snapshots = SnapshotRepository(session)

    def __enter__(self) -> UnitOfWork:
        if self._owns_session:
            self._bind(self._session_factory())
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is not None:
                self.session.rollback()
        finally:
            if self._owns_session:
                self.session.close()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
