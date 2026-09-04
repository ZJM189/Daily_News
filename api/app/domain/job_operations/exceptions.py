from app.domain.exceptions import DomainError


class JobRunNotFound(DomainError):
    """Raised when a job run does not exist."""


class SchedulerConfigNotFound(DomainError):
    """Raised when a scheduler config does not exist."""


class InvalidCronExpression(DomainError):
    """Raised when a cron expression is invalid."""


class InvalidTimezone(DomainError):
    """Raised when a timezone is invalid."""
