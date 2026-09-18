"""Schema estrito da resposta da IA.

Com Structured Outputs em modo strict a OpenAI exige que todo objeto declare
additionalProperties false e liste todas as propriedades em required. O schema abaixo
segue essa restricao, e o modelo Pydantic ao lado revalida a resposta antes de persistir.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

AI_SCHEMA_NAME = "lotto_lab_analysis"


class NumberEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n: int
    evidence: str


class OverdueNumber(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n: int
    delay_ratio: float


class HistoryReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hot_numbers: list[NumberEvidence]
    cold_numbers: list[NumberEvidence]
    overdue_numbers: list[OverdueNumber]
    pattern_notes: list[str]
    sequence_notes: list[str]


class RankedGame(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    rank: int
    statistical_fit: float
    already_drawn: bool
    rationale: str


class SetDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    avg_overlap: float
    coverage: list[int]
    warnings: list[str]


class BudgetNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_cost: float
    within_limit: bool
    note: str


class AIAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overview: str
    history_reading: HistoryReading
    ranked_games: list[RankedGame]
    set_diagnostics: SetDiagnostics
    budget: BudgetNote
    disclaimer: str


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def response_json_schema() -> dict[str, Any]:
    """Schema enviado em response_format, com strict true."""
    number_evidence = _object({"n": {"type": "integer"}, "evidence": {"type": "string"}})
    overdue = _object({"n": {"type": "integer"}, "delay_ratio": {"type": "number"}})

    return {
        "name": AI_SCHEMA_NAME,
        "strict": True,
        "schema": _object(
            {
                "overview": {"type": "string"},
                "history_reading": _object(
                    {
                        "hot_numbers": {"type": "array", "items": number_evidence},
                        "cold_numbers": {"type": "array", "items": number_evidence},
                        "overdue_numbers": {"type": "array", "items": overdue},
                        "pattern_notes": {"type": "array", "items": {"type": "string"}},
                        "sequence_notes": {"type": "array", "items": {"type": "string"}},
                    }
                ),
                "ranked_games": {
                    "type": "array",
                    "items": _object(
                        {
                            "id": {"type": "string"},
                            "rank": {"type": "integer"},
                            "statistical_fit": {"type": "number"},
                            "already_drawn": {"type": "boolean"},
                            "rationale": {"type": "string"},
                        }
                    ),
                },
                "set_diagnostics": _object(
                    {
                        "avg_overlap": {"type": "number"},
                        "coverage": {"type": "array", "items": {"type": "integer"}},
                        "warnings": {"type": "array", "items": {"type": "string"}},
                    }
                ),
                "budget": _object(
                    {
                        "total_cost": {"type": "number"},
                        "within_limit": {"type": "boolean"},
                        "note": {"type": "string"},
                    }
                ),
                "disclaimer": {"type": "string"},
            }
        ),
    }
