from app.domain.exceptions import DomainError


class SourceNotFound(DomainError):
    """Raised when a source does not exist."""


class CredentialNotFound(DomainError):
    """Raised when a source credential does not exist."""
