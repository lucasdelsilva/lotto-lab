"""Import com substituicao total. A garantia central e que arquivo invalido nao destroi
o historico existente e que o delete nunca vaza para outra modalidade."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.application.use_cases.import_draws import import_draws
from app.core.errors import ImportValidationError
from app.domain.enums import Modality
from app.infrastructure.db.uow import UnitOfWork
from tests.integration.test_parser import MEGA_HEADER, MEGA_ROWS, build_xlsx

LOTOFACIL_HEADER = ["Concurso", "Data Sorteio", *[f"Bola{i}" for i in range(1, 16)]]
LOTOFACIL_ROWS = [
    [1, "29/09/2003", *range(1, 16)],
    [2, "06/10/2003", *range(5, 20)],
]


@pytest.fixture
def uow(session: Session) -> UnitOfWork:
    return UnitOfWork.from_session(session)


def test_importa_arquivo_valido(uow: UnitOfWork) -> None:
    summary = import_draws(
        uow, Modality.MEGA_SENA, "mega.xlsx", build_xlsx(MEGA_HEADER, MEGA_ROWS)
    )

    assert summary.rows_imported == 3
    assert summary.rows_deleted == 0
    assert summary.first_contest == 1
    assert summary.last_contest == 3
    assert summary.first_drawn_at == "1996-03-11"
    assert uow.draws.count(Modality.MEGA_SENA) == 3


def test_segunda_importacao_substitui_o_historico(uow: UnitOfWork) -> None:
    import_draws(uow, Modality.MEGA_SENA, "mega.xlsx", build_xlsx(MEGA_HEADER, MEGA_ROWS))

    novas = [[10, "01/05/1996", 1, 2, 3, 4, 5, 6]]
    summary = import_draws(uow, Modality.MEGA_SENA, "mega2.xlsx", build_xlsx(MEGA_HEADER, novas))

    assert summary.rows_deleted == 3
    assert summary.rows_imported == 1
    assert uow.draws.count(Modality.MEGA_SENA) == 1
    assert uow.draws.latest(Modality.MEGA_SENA).contest_no == 10  # type: ignore[union-attr]


def test_delete_nao_vaza_para_outra_modalidade(uow: UnitOfWork) -> None:
    import_draws(uow, Modality.MEGA_SENA, "mega.xlsx", build_xlsx(MEGA_HEADER, MEGA_ROWS))
    import_draws(
        uow, Modality.LOTOFACIL, "lf.xlsx", build_xlsx(LOTOFACIL_HEADER, LOTOFACIL_ROWS)
    )

    assert uow.draws.count(Modality.MEGA_SENA) == 3
    assert uow.draws.count(Modality.LOTOFACIL) == 2

    # Reimportar a Mega apaga apenas a Mega.
    import_draws(
        uow, Modality.MEGA_SENA, "mega2.xlsx", build_xlsx(MEGA_HEADER, [MEGA_ROWS[0]])
    )

    assert uow.draws.count(Modality.MEGA_SENA) == 1
    assert uow.draws.count(Modality.LOTOFACIL) == 2


def test_arquivo_invalido_preserva_o_historico(uow: UnitOfWork) -> None:
    import_draws(uow, Modality.MEGA_SENA, "mega.xlsx", build_xlsx(MEGA_HEADER, MEGA_ROWS))
    assert uow.draws.count(Modality.MEGA_SENA) == 3

    invalidas = [[9, "01/05/1996", 4, 5, 30, 33, 41, 99]]
    with pytest.raises(ImportValidationError) as exc:
        import_draws(uow, Modality.MEGA_SENA, "ruim.xlsx", build_xlsx(MEGA_HEADER, invalidas))

    assert exc.value.status_code == 422
    assert exc.value.errors
    # Nada foi apagado nem inserido.
    assert uow.draws.count(Modality.MEGA_SENA) == 3
    assert uow.draws.latest(Modality.MEGA_SENA).contest_no == 3  # type: ignore[union-attr]


def test_concurso_duplicado_preserva_o_historico(uow: UnitOfWork) -> None:
    import_draws(uow, Modality.MEGA_SENA, "mega.xlsx", build_xlsx(MEGA_HEADER, MEGA_ROWS))

    duplicadas = [*MEGA_ROWS, [2, "01/04/1996", 1, 2, 3, 4, 5, 6]]
    with pytest.raises(ImportValidationError):
        import_draws(
            uow, Modality.MEGA_SENA, "dup.xlsx", build_xlsx(MEGA_HEADER, duplicadas)
        )

    assert uow.draws.count(Modality.MEGA_SENA) == 3


def test_registra_o_lote_de_importacao(uow: UnitOfWork) -> None:
    summary = import_draws(
        uow, Modality.MEGA_SENA, "mega.xlsx", build_xlsx(MEGA_HEADER, MEGA_ROWS)
    )
    batches = uow.draws.list_batches(Modality.MEGA_SENA)

    assert len(batches) == 1
    assert batches[0].filename == "mega.xlsx"
    assert batches[0].file_hash == summary.file_hash
    assert batches[0].rows_imported == 3


def test_importacao_invalida_o_snapshot(uow: UnitOfWork) -> None:
    import_draws(uow, Modality.MEGA_SENA, "mega.xlsx", build_xlsx(MEGA_HEADER, MEGA_ROWS))
    uow.snapshots.save(
        Modality.MEGA_SENA, history_hash="abc", draws_count=3, payload={"stale": True}
    )
    uow.commit()
    assert uow.snapshots.get(Modality.MEGA_SENA) is not None

    import_draws(
        uow, Modality.MEGA_SENA, "mega2.xlsx", build_xlsx(MEGA_HEADER, [MEGA_ROWS[0]])
    )

    assert uow.snapshots.get(Modality.MEGA_SENA) is None


def test_super_sete_guarda_as_colunas(uow: UnitOfWork) -> None:
    header = ["Concurso", "Data do Sorteio", *[f"Coluna{i}" for i in range(1, 8)]]
    rows = [[1, "02/10/2020", 5, 3, 0, 9, 1, 1, 7]]
    import_draws(uow, Modality.SUPER_SETE, "ss.xlsx", build_xlsx(header, rows))

    draw = uow.draws.latest(Modality.SUPER_SETE)
    assert draw is not None
    assert draw.numbers == (5, 3, 0, 9, 1, 1, 7)
    assert draw.extras == {"columns": [5, 3, 0, 9, 1, 1, 7]}


def test_dia_de_sorte_guarda_o_mes(uow: UnitOfWork) -> None:
    header = ["Concurso", "Data Sorteio", *[f"Bola{i}" for i in range(1, 8)], "Mês da Sorte"]
    rows = [[1, "16/03/2018", 3, 7, 11, 17, 21, 25, 31, "setembro"]]
    import_draws(uow, Modality.DIA_DE_SORTE, "dds.xlsx", build_xlsx(header, rows))

    draw = uow.draws.latest(Modality.DIA_DE_SORTE)
    assert draw is not None
    assert draw.month_of_luck == 9
