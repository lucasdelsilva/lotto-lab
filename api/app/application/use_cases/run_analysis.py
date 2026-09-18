"""Snapshot de analise, calculado uma vez por historico e reaproveitado.

O cache e invalidado por hash do historico, nao por tempo: enquanto os concursos forem os
mesmos, o resultado e o mesmo, e recalcular seria desperdicio.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np

from app.analytics import supersete
from app.analytics.cooccurrence import cooccurrence_report, top_triples
from app.analytics.delays import delay_matrix, delay_report
from app.analytics.frequency import classify, frequency_report, z_scores
from app.analytics.patterns import pattern_report
from app.analytics.sequences import sequence_report
from app.core.errors import NotFoundError
from app.core.logging import timed
from app.domain.entities import Draw
from app.domain.enums import Modality
from app.domain.rules import ModalityRule, rule_for
from app.infrastructure.db.uow import UnitOfWork

logger = logging.getLogger(__name__)

REFERENCE_WINDOW = 50


@dataclass(frozen=True, slots=True)
class HistoryData:
    """Historico ja convertido para arrays, pronto para o pacote analytics."""

    draws: np.ndarray
    contests: np.ndarray
    months: list[int]
    rule: ModalityRule
    first_drawn_at: str | None
    last_drawn_at: str | None

    @property
    def total(self) -> int:
        return int(self.draws.shape[0])

    @property
    def history_hash(self) -> str:
        return history_hash(self.draws, self.contests)


def history_hash(draws: np.ndarray, contests: np.ndarray) -> str:
    """Impressao digital do historico. Muda se qualquer concurso mudar."""
    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(contests, dtype=np.int64).tobytes())
    digest.update(np.ascontiguousarray(draws, dtype=np.int64).tobytes())
    return digest.hexdigest()


def load_history(uow: UnitOfWork, modality: Modality) -> HistoryData:
    rule = rule_for(modality)
    rows: list[Draw] = uow.draws.list_all(modality)
    if not rows:
        raise NotFoundError(
            f"Nenhum concurso importado para {modality.label}. "
            "Importe a planilha da modalidade antes de analisar."
        )
    draws = np.asarray([row.numbers for row in rows], dtype=np.int64)
    contests = np.asarray([row.contest_no for row in rows], dtype=np.int64)
    months = [row.month_of_luck or 0 for row in rows if row.month_of_luck]
    return HistoryData(
        draws=draws,
        contests=contests,
        months=months,
        rule=rule,
        first_drawn_at=rows[0].drawn_at.isoformat(),
        last_drawn_at=rows[-1].drawn_at.isoformat(),
    )


def number_stats(history: HistoryData, window: int = REFERENCE_WINDOW) -> list[dict[str, Any]]:
    """Uma linha por dezena, juntando frequencia, atraso e temperatura."""
    rule = history.rule
    frequency = frequency_report(history.draws, rule)
    delays = delay_report(history.draws, rule)
    z_window = z_scores(history.draws, rule, window)

    return [
        {
            "n": int(number),
            "freq": int(frequency.absolute[index]),
            "freq_rate": round(float(frequency.relative[index]), 6),
            f"z_{window}": round(float(z_window[index]), 4),
            "temperature": classify(float(z_window[index])).value,
            "current_delay": int(delays.current[index]),
            "avg_delay": round(float(delays.average[index]), 3),
            "max_delay": int(delays.maximum[index]),
            "delay_ratio": round(float(delays.ratio[index]), 3),
        }
        for index, number in enumerate(frequency.numbers)
    ]


def month_stats(history: HistoryData) -> list[dict[str, Any]]:
    """Distribuicao do mes da sorte, usada apenas pelo Dia de Sorte."""
    if not history.months:
        return []
    months = np.asarray(history.months, dtype=np.int64)
    counts = np.bincount(months, minlength=13)[1:]
    total = int(months.shape[0])
    rows = []
    for month in range(1, 13):
        appearances = np.flatnonzero(months == month)
        current_delay = total - 1 - int(appearances[-1]) if appearances.size else total
        rows.append(
            {
                "month": month,
                "count": int(counts[month - 1]),
                "rate": round(float(counts[month - 1]) / total, 6) if total else 0.0,
                "current_delay": current_delay,
            }
        )
    return rows


def build_payload(history: HistoryData, window: int = REFERENCE_WINDOW) -> dict[str, Any]:
    rule = history.rule
    payload: dict[str, Any] = {
        "modality": rule.modality.value,
        "computed_at": datetime.now(UTC).isoformat(),
        "window": window,
        "history_meta": {
            "total_draws": history.total,
            "first_contest": int(history.contests[0]),
            "last_contest": int(history.contests[-1]),
            "first_drawn_at": history.first_drawn_at,
            "last_drawn_at": history.last_drawn_at,
        },
    }

    if rule.is_column_based:
        payload["supersete"] = supersete.supersete_report(
            history.draws, history.contests, rule, window
        )
        return payload

    frequency = frequency_report(history.draws, rule)
    delays = delay_report(history.draws, rule)
    cooccurrence = cooccurrence_report(history.draws, rule)

    payload["numbers"] = number_stats(history, window)
    payload["frequency"] = frequency.as_dict()
    payload["delays"] = delays.as_dict()
    payload["delay_heatmap"] = delay_matrix(history.draws, rule, last_n=60).tolist()
    payload["patterns"] = pattern_report(history.draws, rule)
    payload["sequences"] = sequence_report(history.draws, rule)
    payload["pairs"] = cooccurrence.as_dict()
    payload["triples"] = top_triples(history.draws, limit=50)
    if rule.modality is Modality.DIA_DE_SORTE:
        payload["months"] = month_stats(history)
    return payload


def run_analysis(uow: UnitOfWork, modality: Modality, refresh: bool = False) -> dict[str, Any]:
    history = load_history(uow, modality)
    digest = history.history_hash

    if not refresh:
        cached = uow.snapshots.get_fresh(modality, digest)
        if cached is not None:
            cached["cached"] = True
            return cached

    with timed(logger, "run_analysis", modality=modality.value, draws=history.total):
        payload = build_payload(history)

    uow.snapshots.save(
        modality, history_hash=digest, draws_count=history.total, payload=payload
    )
    uow.commit()
    payload["cached"] = False
    return payload
