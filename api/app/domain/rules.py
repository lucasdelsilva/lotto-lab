"""Regras das modalidades. Fonte unica da verdade do dominio.

O preco nao fica preso na regra de negocio: cada modalidade carrega uma tabela de
precos com data de vigencia, e o custo sempre consulta a tabela por data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from types import MappingProxyType
from typing import Any

from app.domain.enums import Modality


@dataclass(frozen=True, slots=True)
class PriceTier:
    """Preco base de uma aposta simples valido a partir de uma data."""

    valid_from: date
    price: Decimal


@dataclass(frozen=True, slots=True)
class BoardLayout:
    """Layout do volante fisico, usado para quadrantes, linhas e colunas cheias."""

    rows: int
    cols: int

    def position(self, number: int, universe_min: int) -> tuple[int, int]:
        index = number - universe_min
        return divmod(index, self.cols)

    def quadrant(self, number: int, universe_min: int) -> int:
        """Indice 0 a 3, varrendo superior esquerdo, superior direito, inferior esquerdo,
        inferior direito. Com dimensao impar a metade superior/esquerda fica menor."""
        row, col = self.position(number, universe_min)
        top = 0 if row < self.rows // 2 else 1
        left = 0 if col < self.cols // 2 else 1
        return top * 2 + left


@dataclass(frozen=True, slots=True)
class ModalityRule:
    modality: Modality
    universe_min: int
    universe_max: int
    min_pick: int
    max_pick: int
    base_hits: int
    prices: tuple[PriceTier, ...]
    board: BoardLayout | None = None
    columns: int = 0
    column_min_pick: int = 0
    column_max_pick: int = 0
    column_digit_min: int = 0
    column_digit_max: int = 0
    extra_schema: dict[str, Any] = field(default_factory=dict)

    @property
    def universe_size(self) -> int:
        return self.universe_max - self.universe_min + 1

    @property
    def is_column_based(self) -> bool:
        return self.columns > 0

    @property
    def base_price(self) -> Decimal:
        return self.prices[-1].price

    def price_at(self, moment: date | None = None) -> Decimal:
        """Preco vigente na data informada. Sem data, usa a tabela mais recente."""
        if moment is None:
            return self.base_price
        applicable = [tier for tier in self.prices if tier.valid_from <= moment]
        if not applicable:
            return self.prices[0].price
        return max(applicable, key=lambda tier: tier.valid_from).price

    def contains(self, number: int) -> bool:
        return self.universe_min <= number <= self.universe_max

    def universe(self) -> range:
        return range(self.universe_min, self.universe_max + 1)


_MEGA = ModalityRule(
    modality=Modality.MEGA_SENA,
    universe_min=1,
    universe_max=60,
    min_pick=6,
    max_pick=20,
    base_hits=6,
    prices=(
        PriceTier(date(2024, 1, 1), Decimal("5.00")),
        PriceTier(date(2025, 1, 1), Decimal("6.00")),
    ),
    board=BoardLayout(rows=6, cols=10),
)

_LOTOFACIL = ModalityRule(
    modality=Modality.LOTOFACIL,
    universe_min=1,
    universe_max=25,
    min_pick=15,
    max_pick=20,
    base_hits=15,
    prices=(
        PriceTier(date(2024, 1, 1), Decimal("3.00")),
        PriceTier(date(2025, 1, 1), Decimal("3.50")),
    ),
    board=BoardLayout(rows=5, cols=5),
)

_QUINA = ModalityRule(
    modality=Modality.QUINA,
    universe_min=1,
    universe_max=80,
    min_pick=5,
    max_pick=15,
    base_hits=5,
    prices=(
        PriceTier(date(2024, 1, 1), Decimal("2.50")),
        PriceTier(date(2025, 1, 1), Decimal("3.00")),
    ),
    board=BoardLayout(rows=8, cols=10),
)

_DIA_DE_SORTE = ModalityRule(
    modality=Modality.DIA_DE_SORTE,
    universe_min=1,
    universe_max=31,
    min_pick=7,
    max_pick=15,
    base_hits=7,
    prices=(PriceTier(date(2024, 1, 1), Decimal("2.50")),),
    board=BoardLayout(rows=4, cols=8),
    extra_schema={
        "month": {
            "type": "integer",
            "required": True,
            "count": 1,
            "min": 1,
            "max": 12,
            "label": "Mes da Sorte",
        }
    },
)

_SUPER_SETE = ModalityRule(
    modality=Modality.SUPER_SETE,
    universe_min=0,
    universe_max=9,
    min_pick=7,
    max_pick=21,
    base_hits=7,
    prices=(
        PriceTier(date(2024, 1, 1), Decimal("2.50")),
        PriceTier(date(2025, 1, 1), Decimal("3.00")),
    ),
    board=None,
    columns=7,
    column_min_pick=1,
    column_max_pick=3,
    column_digit_min=0,
    column_digit_max=9,
    extra_schema={
        "columns": {
            "type": "array",
            "required": True,
            "length": 7,
            "item_min": 0,
            "item_max": 9,
            "label": "Colunas",
        }
    },
)

MODALITY_RULES: MappingProxyType[Modality, ModalityRule] = MappingProxyType(
    {
        Modality.MEGA_SENA: _MEGA,
        Modality.LOTOFACIL: _LOTOFACIL,
        Modality.QUINA: _QUINA,
        Modality.DIA_DE_SORTE: _DIA_DE_SORTE,
        Modality.SUPER_SETE: _SUPER_SETE,
    }
)


def rule_for(modality: Modality) -> ModalityRule:
    return MODALITY_RULES[modality]
