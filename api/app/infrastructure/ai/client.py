"""Cliente da OpenAI com Structured Outputs e degradacao graciosa.

A IA nao gera numeros. Ela recebe estatisticas ja calculadas e jogos ja gerados, e produz
leitura do historico e ranking. Se a chave nao existir, se o timeout estourar ou se a
resposta nao bater com o schema, a aplicacao continua funcionando e devolve
ai_available false.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from pydantic import ValidationError as PydanticValidationError

from app.core.config import get_settings
from app.infrastructure.ai.schemas import AIAnalysis, response_json_schema

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompts" / "analyst.md"
BACKOFF_SECONDS = 1.5


@dataclass(frozen=True, slots=True)
class AIResult:
    available: bool
    analysis: AIAnalysis | None = None
    error: str | None = None
    model: str | None = None
    tokens: dict[str, int] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ai_available": self.available,
            "model": self.model,
            "tokens": self.tokens,
            "error": self.error,
            "analysis": self.analysis.model_dump() if self.analysis else None,
        }


@lru_cache(maxsize=1)
def system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


class AIAnalyst:
    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def enabled(self) -> bool:
        return self._settings.ai_enabled

    def review(self, payload: dict[str, Any]) -> AIResult:
        if not self.enabled:
            return AIResult(
                available=False,
                error="Chave da OpenAI ausente. A analise deterministica continua disponivel.",
            )

        try:
            from openai import OpenAI
        except ImportError:  # pragma: no cover - dependencia declarada no pyproject
            return AIResult(available=False, error="SDK da OpenAI nao instalado.")

        client = OpenAI(
            api_key=self._settings.openai_api_key,
            timeout=self._settings.openai_timeout_seconds,
            max_retries=0,
        )

        attempts = self._settings.openai_max_retries + 1
        last_error: str | None = None

        for attempt in range(attempts):
            try:
                started = time.perf_counter()
                # O SDK tipa messages e response_format com TypedDicts extensos; o cast
                # mantem a chamada legivel sem abrir mao do mypy strict no resto do modulo.
                completion = client.chat.completions.create(
                    model=self._settings.openai_model,
                    temperature=self._settings.openai_temperature,
                    messages=cast(
                        Any,
                        [
                            {"role": "system", "content": system_prompt()},
                            {
                                "role": "user",
                                "content": json.dumps(payload, ensure_ascii=False, default=str),
                            },
                        ],
                    ),
                    response_format=cast(
                        Any,
                        {"type": "json_schema", "json_schema": response_json_schema()},
                    ),
                )
                content = completion.choices[0].message.content or "{}"
                analysis = AIAnalysis.model_validate_json(content)
                usage = completion.usage
                tokens = (
                    {
                        "prompt": usage.prompt_tokens,
                        "completion": usage.completion_tokens,
                        "total": usage.total_tokens,
                    }
                    if usage
                    else None
                )
                logger.info(
                    "ai.review.completed",
                    extra={
                        "model": self._settings.openai_model,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                        "tokens": tokens,
                        "attempt": attempt + 1,
                    },
                )
                return AIResult(
                    available=True,
                    analysis=analysis,
                    model=self._settings.openai_model,
                    tokens=tokens,
                )
            except PydanticValidationError as exc:
                last_error = f"Resposta fora do schema: {exc.error_count()} erro(s)."
                logger.warning("ai.schema.invalid", extra={"attempt": attempt + 1})
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "ai.request.failed", extra={"attempt": attempt + 1, "error": str(exc)}
                )

            if attempt < attempts - 1:
                time.sleep(BACKOFF_SECONDS * (2**attempt))

        return AIResult(available=False, error=last_error)


@lru_cache(maxsize=1)
def get_analyst() -> AIAnalyst:
    return AIAnalyst()
