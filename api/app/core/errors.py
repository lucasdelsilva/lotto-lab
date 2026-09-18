"""Excecoes de dominio. A borda HTTP traduz cada uma para um status especifico."""

from typing import Any


class DomainError(Exception):
    """Base de todos os erros previstos do dominio."""

    code: str = "domain_error"
    status_code: int = 400
    title: str = "Erro de dominio"

    def __init__(self, detail: str, *, extra: dict[str, Any] | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.extra = extra or {}


class ValidationError(DomainError):
    code = "validation_error"
    status_code = 422
    title = "Dados invalidos"


class ImportValidationError(ValidationError):
    """Falha na validacao do arquivo importado. Nenhum dado foi tocado no banco."""

    code = "import_validation_error"
    title = "Arquivo de importacao invalido"

    def __init__(self, detail: str, *, errors: list[dict[str, Any]]) -> None:
        super().__init__(detail, extra={"errors": errors})
        self.errors = errors


class NotFoundError(DomainError):
    code = "not_found"
    status_code = 404
    title = "Recurso nao encontrado"


class BusinessRuleError(DomainError):
    code = "business_rule_violation"
    status_code = 409
    title = "Regra de negocio violada"


class BudgetExceededError(BusinessRuleError):
    code = "budget_exceeded"
    title = "Orcamento estourado"


class GenerationExhaustedError(BusinessRuleError):
    code = "generation_exhausted"
    title = "Nao foi possivel gerar jogos com os filtros informados"


class AIUnavailableError(DomainError):
    code = "ai_unavailable"
    status_code = 503
    title = "Camada de IA indisponivel"
