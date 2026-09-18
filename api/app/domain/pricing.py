"""Combinatoria e custo das apostas. Sempre Decimal, nunca float."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.core.errors import ValidationError
from app.domain.enums import Modality
from app.domain.rules import ModalityRule, rule_for

CENTS = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    """Arredonda para duas casas com ROUND_HALF_UP."""
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def combinations(n: int, k: int) -> int:
    if n < 0 or k < 0:
        raise ValidationError("Combinatoria exige valores nao negativos.")
    if k > n:
        return 0
    return math.comb(n, k)


@dataclass(frozen=True, slots=True)
class BetCost:
    """Custo de uma unica aposta (um volante)."""

    modality: Modality
    numbers: int
    combinations: int
    base_price: Decimal
    total: Decimal
    column_picks: tuple[int, ...] | None = None

    def scaled(self, games: int) -> Decimal:
        """Custo de um lote com `games` apostas iguais em tamanho."""
        if games < 0:
            raise ValidationError("Quantidade de jogos nao pode ser negativa.")
        return money(self.total * Decimal(games))


def distribute_columns(total_numbers: int, rule: ModalityRule) -> tuple[int, ...]:
    """Distribuicao padrao de digitos por coluna do Super Sete.

    Comeca com um digito por coluna e espalha o excedente em rodizio da esquerda para a
    direita. E a mesma convencao da tabela oficial de precos: 9 numeros viram 4 jogos,
    14 numeros viram 128 jogos, 21 numeros viram 2187 jogos.
    """
    columns = rule.columns
    if total_numbers < columns * rule.column_min_pick:
        raise ValidationError(
            f"O Super Sete exige pelo menos {columns * rule.column_min_pick} numeros."
        )
    if total_numbers > columns * rule.column_max_pick:
        raise ValidationError(
            f"O Super Sete aceita no maximo {columns * rule.column_max_pick} numeros."
        )
    picks = [rule.column_min_pick] * columns
    remaining = total_numbers - sum(picks)
    index = 0
    while remaining > 0:
        if picks[index] < rule.column_max_pick:
            picks[index] += 1
            remaining -= 1
        index = (index + 1) % columns
    return tuple(picks)


def _column_picks_from_extras(
    numbers: int, rule: ModalityRule, extras: dict[str, Any] | None
) -> tuple[int, ...]:
    raw = (extras or {}).get("column_picks") or (extras or {}).get("columns")
    if raw is None:
        return distribute_columns(numbers, rule)
    if isinstance(raw, list) and raw and isinstance(raw[0], list):
        picks = tuple(len(set(column)) for column in raw)
    else:
        picks = tuple(int(item) for item in raw)
    if len(picks) != rule.columns:
        raise ValidationError(f"O Super Sete exige exatamente {rule.columns} colunas.")
    for count in picks:
        if not rule.column_min_pick <= count <= rule.column_max_pick:
            raise ValidationError(
                "Cada coluna do Super Sete aceita de "
                f"{rule.column_min_pick} a {rule.column_max_pick} digitos."
            )
    return picks


def validate_pick_count(modality: Modality, numbers: int) -> ModalityRule:
    rule = rule_for(modality)
    if not rule.min_pick <= numbers <= rule.max_pick:
        raise ValidationError(
            f"{modality.label} aceita de {rule.min_pick} a {rule.max_pick} numeros, "
            f"recebido {numbers}."
        )
    return rule


def game_count(modality: Modality, numbers: int, extras: dict[str, Any] | None = None) -> int:
    """Quantidade de apostas simples equivalentes a um volante com `numbers` numeros."""
    rule = validate_pick_count(modality, numbers)
    if rule.is_column_based:
        picks = _column_picks_from_extras(numbers, rule, extras)
        return math.prod(picks)
    return combinations(numbers, rule.base_hits)


def preview_cost(
    modality: Modality,
    numbers: int,
    extras: dict[str, Any] | None = None,
    moment: date | None = None,
) -> BetCost:
    """Custo de um volante. E o que o front chama em tempo real enquanto o usuario escolhe."""
    rule = validate_pick_count(modality, numbers)
    price = rule.price_at(moment)
    picks: tuple[int, ...] | None = None
    if rule.is_column_based:
        picks = _column_picks_from_extras(numbers, rule, extras)
        count = math.prod(picks)
    else:
        count = combinations(numbers, rule.base_hits)
    return BetCost(
        modality=modality,
        numbers=numbers,
        combinations=count,
        base_price=price,
        total=money(price * Decimal(count)),
        column_picks=picks,
    )


def batch_cost(
    modality: Modality,
    numbers: int,
    games: int,
    extras: dict[str, Any] | None = None,
    moment: date | None = None,
) -> tuple[BetCost, Decimal]:
    """Custo por volante e custo total de um lote de `games` volantes."""
    unit = preview_cost(modality, numbers, extras, moment)
    return unit, unit.scaled(games)
