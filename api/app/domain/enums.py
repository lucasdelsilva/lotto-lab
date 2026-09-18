"""Enumeracoes de dominio."""

from enum import StrEnum


class Modality(StrEnum):
    MEGA_SENA = "MEGA_SENA"
    LOTOFACIL = "LOTOFACIL"
    QUINA = "QUINA"
    DIA_DE_SORTE = "DIA_DE_SORTE"
    SUPER_SETE = "SUPER_SETE"

    @property
    def label(self) -> str:
        return _LABELS[self]


_LABELS: dict[Modality, str] = {
    Modality.MEGA_SENA: "Mega-Sena",
    Modality.LOTOFACIL: "Lotofacil",
    Modality.QUINA: "Quina",
    Modality.DIA_DE_SORTE: "Dia de Sorte",
    Modality.SUPER_SETE: "Super Sete",
}


class Profile(StrEnum):
    BALANCED = "balanced"
    HOT = "hot"
    COLD = "cold"
    PATTERN = "pattern"
    UNIFORM = "uniform"


class AlreadyDrawnPolicy(StrEnum):
    REJECT = "reject"
    FLAG = "flag"


class ImportStatus(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BetStatus(StrEnum):
    PENDING = "PENDING"
    CHECKED = "CHECKED"
    CANCELLED = "CANCELLED"


class NumberTemperature(StrEnum):
    HOT = "hot"
    COLD = "cold"
    NEUTRAL = "neutral"


class FilterId(StrEnum):
    """Filtros rigidos do gerador, um por criterio de analise."""

    EVEN_ODD = "even_odd"
    SUM = "sum"
    ROWS = "rows"
    COLUMNS = "columns"
    REPEATED = "repeated"
    CONSECUTIVE = "consecutive"
    GAPS = "gaps"
    FIBONACCI = "fibonacci"
    PRIMES = "primes"
    PARETO = "pareto"
    WEIGHTS = "weights"
