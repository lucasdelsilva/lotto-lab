"""Snapshot de analise e recortes por assunto."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.filters import build_bounds, catalog_for, filter_efficiency
from app.analytics.scoring import NumberScorer, normalize, weights_for
from app.application.use_cases.run_analysis import load_history, run_analysis
from app.domain.enums import Modality, Profile
from app.infrastructure.db.session import get_db
from app.infrastructure.db.uow import UnitOfWork

router = APIRouter(prefix="/modalities/{modality}", tags=["analysis"])


def _analysis(session: Session, modality: Modality, refresh: bool) -> dict[str, Any]:
    return run_analysis(UnitOfWork.from_session(session), modality, refresh=refresh)


@router.get("/analysis")
def full_analysis(
    modality: Modality,
    refresh: Annotated[bool, Query(description="Recalcula ignorando o cache")] = False,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    return _analysis(session, modality, refresh)


@router.get("/analysis/numbers")
def numbers_analysis(
    modality: Modality, refresh: bool = False, session: Session = Depends(get_db)
) -> dict[str, Any]:
    payload = _analysis(session, modality, refresh)
    return {
        "modality": payload["modality"],
        "window": payload["window"],
        "history_meta": payload["history_meta"],
        "numbers": payload.get("numbers", []),
        "delay_heatmap": payload.get("delay_heatmap", []),
        "months": payload.get("months", []),
        "supersete": payload.get("supersete"),
    }


@router.get("/analysis/patterns")
def patterns_analysis(
    modality: Modality, refresh: bool = False, session: Session = Depends(get_db)
) -> dict[str, Any]:
    payload = _analysis(session, modality, refresh)
    return {
        "modality": payload["modality"],
        "history_meta": payload["history_meta"],
        "patterns": payload.get("patterns", {}),
        "sequences": payload.get("sequences", {}),
        "supersete": payload.get("supersete"),
    }


@router.get("/analysis/pairs")
def pairs_analysis(
    modality: Modality, refresh: bool = False, session: Session = Depends(get_db)
) -> dict[str, Any]:
    payload = _analysis(session, modality, refresh)
    return {
        "modality": payload["modality"],
        "history_meta": payload["history_meta"],
        "pairs": payload.get("pairs", {}),
        "triples": payload.get("triples", []),
    }


@router.get("/filters")
def filter_catalog(modality: Modality) -> dict[str, Any]:
    """Catalogo de filtros da modalidade, com rotulo e descricao para a tela."""
    return {"modality": modality.value, "filters": catalog_for(modality)}


@router.get("/filters/efficiency")
def filters_efficiency(
    modality: Modality,
    sample: Annotated[int, Query(ge=10, le=1000)] = 100,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    """Quantos dos ultimos concursos reais passariam em cada filtro.

    Filtro que reprova muito resultado que de fato saiu esta cortando jogo bom.
    """
    history = load_history(UnitOfWork.from_session(session), modality)
    rule = history.rule
    scorer = NumberScorer(history.draws, rule, weights_for(Profile.BALANCED))
    scores = normalize(scorer.static_scores().clip(min=0.0))
    bounds = build_bounds(history.draws, rule, scores)
    linhas = filter_efficiency(history.draws, rule, bounds, scores, sample=sample)
    geral = (
        round(sum(item["efficiency"] for item in linhas) / len(linhas), 4) if linhas else 0.0
    )
    return {
        "modality": modality.value,
        "sample": min(sample, history.total),
        "filters": linhas,
        "overall": geral,
        "bounds": bounds.as_dict(),
    }
