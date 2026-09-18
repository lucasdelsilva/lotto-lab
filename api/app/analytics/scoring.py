"""Score composto por dezena, de 0 a 1.

O score combina cinco sinais normalizados por min-max sobre o universo da modalidade:

    score(d) = w_freq   * norm(freq_rel_janela(d))
             + w_delay  * norm(delay_ratio(d))
             + w_markov * norm(markov_prob(d))
             + w_cooc   * norm(lift_medio_com_selecionadas(d))
             + w_global * norm(freq_rel_total(d))

Quatro desses sinais dependem apenas do historico e sao calculados uma unica vez. O quinto,
o de co-ocorrencia, depende das dezenas ja escolhidas no jogo em construcao, entao precisa
ser recalculado a cada dezena adicionada. E por isso que o scorer separa a parte estatica
da parte dinamica.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from app.analytics.cooccurrence import (
    average_lift_with,
    markov_transition,
    pair_counts,
    pair_lift,
)
from app.analytics.delays import delay_report
from app.analytics.frequency import FloatArray, IntArray, relative_frequency, window_frequency
from app.domain.enums import Profile
from app.domain.rules import ModalityRule

DEFAULT_WINDOW = 50


@dataclass(frozen=True, slots=True)
class ProfileWeights:
    freq: float = 0.0
    delay: float = 0.0
    markov: float = 0.0
    cooc: float = 0.0
    global_freq: float = 0.0

    @property
    def is_uniform(self) -> bool:
        return self.freq == self.delay == self.markov == self.cooc == self.global_freq == 0.0

    def as_dict(self) -> dict[str, float]:
        return {
            "freq": self.freq,
            "delay": self.delay,
            "markov": self.markov,
            "cooc": self.cooc,
            "global": self.global_freq,
        }


PROFILE_WEIGHTS: dict[Profile, ProfileWeights] = {
    Profile.BALANCED: ProfileWeights(
        freq=0.25, delay=0.25, markov=0.15, cooc=0.15, global_freq=0.20
    ),
    Profile.HOT: ProfileWeights(freq=0.50, delay=0.05, markov=0.20, cooc=0.15, global_freq=0.10),
    Profile.COLD: ProfileWeights(
        freq=0.05, delay=0.55, markov=0.10, cooc=0.10, global_freq=0.20
    ),
    Profile.PATTERN: ProfileWeights(
        freq=0.15, delay=0.15, markov=0.20, cooc=0.40, global_freq=0.10
    ),
    Profile.UNIFORM: ProfileWeights(),
}


def normalize(values: FloatArray) -> FloatArray:
    """Min-max sobre o universo. Serie constante vira zero, sem divisao por zero."""
    if values.size == 0:
        return values
    lowest = float(values.min())
    highest = float(values.max())
    if highest - lowest <= 0:
        return np.zeros_like(values, dtype=np.float64)
    return (values - lowest) / (highest - lowest)


def weights_for(profile: Profile, overrides: dict[str, float] | None = None) -> ProfileWeights:
    base = PROFILE_WEIGHTS[profile]
    if not overrides:
        return base
    return ProfileWeights(
        freq=float(overrides.get("freq", base.freq)),
        delay=float(overrides.get("delay", base.delay)),
        markov=float(overrides.get("markov", base.markov)),
        cooc=float(overrides.get("cooc", base.cooc)),
        global_freq=float(overrides.get("global", overrides.get("global_freq", base.global_freq))),
    )


class NumberScorer:
    """Calcula o score de cada dezena para um historico e um perfil."""

    def __init__(
        self,
        draws: IntArray,
        rule: ModalityRule,
        weights: ProfileWeights,
        window: int = DEFAULT_WINDOW,
    ) -> None:
        self._rule = rule
        self._weights = weights
        self._size = rule.universe_size

        total_draws = draws.shape[0]
        effective_window = max(1, min(window, total_draws)) if total_draws else 1

        if total_draws == 0:
            zeros = np.zeros(self._size, dtype=np.float64)
            self._static = zeros
            self._lift = np.zeros((self._size, self._size), dtype=np.float64)
            self.components = {
                "freq": zeros,
                "delay": zeros,
                "markov": zeros,
                "global": zeros,
            }
            return

        window_counts = window_frequency(draws, rule, effective_window).astype(np.float64)
        freq_component = normalize(window_counts / float(effective_window))

        delays = delay_report(draws, rule)
        delay_component = normalize(delays.ratio)

        transition = markov_transition(draws, rule)
        last_draw = draws[-1]
        indices = np.asarray(last_draw, dtype=np.int64) - rule.universe_min
        markov_raw = (
            transition[indices].mean(axis=0)
            if transition.size
            else np.zeros(self._size, dtype=np.float64)
        )
        markov_component = normalize(markov_raw)

        global_component = normalize(relative_frequency(draws, rule))

        counts = pair_counts(draws, rule)
        self._lift = pair_lift(counts, total_draws)

        self.components = {
            "freq": freq_component,
            "delay": delay_component,
            "markov": markov_component,
            "global": global_component,
        }

        self._static = (
            weights.freq * freq_component
            + weights.delay * delay_component
            + weights.markov * markov_component
            + weights.global_freq * global_component
        )

    @property
    def weights(self) -> ProfileWeights:
        return self._weights

    def static_scores(self) -> FloatArray:
        return self._static

    def scores(self, selected: Sequence[int] = ()) -> FloatArray:
        """Score final. Com o perfil uniform devolve peso igual para todas as dezenas."""
        if self._weights.is_uniform:
            return np.ones(self._size, dtype=np.float64)
        if not selected or self._weights.cooc == 0.0:
            return self._static
        cooc = normalize(average_lift_with(self._lift, list(selected), self._rule))
        return self._static + self._weights.cooc * cooc

    def score_of(self, numbers: Sequence[int]) -> float:
        """Media do score estatico das dezenas de um jogo pronto."""
        if not numbers:
            return 0.0
        scores = normalize(self._static) if not self._weights.is_uniform else None
        if scores is None:
            return 1.0
        indices = [int(value) - self._rule.universe_min for value in numbers]
        return round(float(scores[indices].mean()), 4)
