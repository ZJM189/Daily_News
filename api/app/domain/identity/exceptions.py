from app.domain.exceptions import DomainError


class AuthenticationFailed(DomainError):
    """Raised when login credentials are invalid."""


class UserDisabled(DomainError):
    """Raised when a disabled user attempts to authenticate."""


class PermissionDenied(DomainError):
    """Raised when a user is not allowed to perform an identity action."""


class UserAlreadyExists(DomainError):
    """Raised when a username or email is already used."""


class UserNotFound(DomainError):
    """Raised when a user does not exist."""


class AdminAlreadyInitialized(DomainError):
    """Raised when trying to create the first admin after users exist."""


class InvalidPassword(DomainError):
    """Raised when a password does not meet policy."""
