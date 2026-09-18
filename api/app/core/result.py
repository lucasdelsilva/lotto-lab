"""Result[T] minimalista. O nucleo devolve Result, a borda HTTP traduz para status."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import NoReturn

from app.core.errors import DomainError


@dataclass(frozen=True, slots=True)
class Success[T]:
    value: T

    @property
    def is_ok(self) -> bool:
        return True

    @property
    def is_failure(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self.value

    def map[U](self, fn: Callable[[T], U]) -> Success[U]:
        return Success(fn(self.value))


@dataclass(frozen=True, slots=True)
class Failure:
    error: DomainError

    @property
    def is_ok(self) -> bool:
        return False

    @property
    def is_failure(self) -> bool:
        return True

    def unwrap(self) -> NoReturn:
        raise self.error

    def map(self, fn: Callable[..., object]) -> Failure:
        return self


type Result[T] = Success[T] | Failure


def ok[T](value: T) -> Success[T]:
    return Success(value)


def fail(error: DomainError) -> Failure:
    return Failure(error)


__all__ = ["Failure", "Result", "Success", "fail", "ok"]
