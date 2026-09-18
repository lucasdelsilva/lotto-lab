"""Log estruturado em JSON, com request_id e duracao das operacoes."""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

_RESERVED = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename", "funcName",
    "levelname", "levelno", "lineno", "module", "msecs", "message", "msg", "name",
    "pathname", "process", "processName", "relativeCreated", "stack_info",
    "thread", "threadName", "taskName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        # Campos livres viajam dentro de "fields" justamente para nao colidirem com os
        # atributos reservados do LogRecord: um extra chamado filename ou module faz o
        # logging levantar KeyError antes de qualquer linha ser emitida.
        fields = record.__dict__.get("fields")
        if isinstance(fields, dict):
            payload.update(fields)
        for key, value in record.__dict__.items():
            if key not in _RESERVED and key != "fields" and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    for noisy in ("uvicorn.access", "uvicorn.error"):
        logging.getLogger(noisy).handlers = [handler]
        logging.getLogger(noisy).propagate = False


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


@contextmanager
def timed(logger: logging.Logger, operation: str, **fields: Any) -> Iterator[dict[str, Any]]:
    """Mede a duracao de uma operacao e registra no log estruturado.

    Os campos recebidos aqui vem do caso de uso e podem ter qualquer nome, inclusive
    nomes reservados pelo logging, entao eles vao empacotados em "fields".
    """
    started = time.perf_counter()
    context: dict[str, Any] = {}
    try:
        yield context
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "operation.completed",
            extra={
                "fields": {
                    "operation": operation,
                    "duration_ms": duration_ms,
                    **fields,
                    **context,
                }
            },
        )
