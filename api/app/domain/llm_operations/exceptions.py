from app.domain.exceptions import DomainError


class LLMProviderNotFound(DomainError):
    """Raised when an LLM provider does not exist."""


class LLMProviderAlreadyExists(DomainError):
    """Raised when an LLM provider name already exists."""
