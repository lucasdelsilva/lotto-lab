"""O log estruturado precisa aguentar qualquer nome de campo vindo do caso de uso."""

from __future__ import annotations

import json
import logging

from app.core.logging import JsonFormatter, request_id_var, timed


def _capture(records: list[logging.LogRecord]) -> logging.Logger:
    logger = logging.getLogger("test.logging")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.INFO)

    class Collector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    logger.addHandler(Collector())
    return logger


def test_campo_com_nome_reservado_nao_quebra_o_log() -> None:
    records: list[logging.LogRecord] = []
    logger = _capture(records)

    # filename, module e name sao atributos do proprio LogRecord.
    with timed(logger, "import_draws", filename="mega.xlsx", module="parser", name="lote"):
        pass

    assert len(records) == 1
    payload = json.loads(JsonFormatter().format(records[0]))
    assert payload["operation"] == "import_draws"
    assert payload["filename"] == "mega.xlsx"
    assert payload["module"] == "parser"
    assert payload["name"] == "lote"
    assert payload["duration_ms"] >= 0


def test_contexto_preenchido_dentro_do_bloco_entra_no_log() -> None:
    records: list[logging.LogRecord] = []
    logger = _capture(records)

    with timed(logger, "generate_games", modality="MEGA_SENA") as context:
        context["attempts"] = 42

    payload = json.loads(JsonFormatter().format(records[0]))
    assert payload["modality"] == "MEGA_SENA"
    assert payload["attempts"] == 42


def test_request_id_entra_em_toda_linha() -> None:
    records: list[logging.LogRecord] = []
    logger = _capture(records)
    token = request_id_var.set("abc123")
    try:
        logger.info("qualquer coisa")
        payload = json.loads(JsonFormatter().format(records[0]))
        assert payload["request_id"] == "abc123"
        assert payload["level"] == "INFO"
    finally:
        request_id_var.reset(token)
