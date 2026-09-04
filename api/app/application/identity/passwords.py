from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from app.domain.identity.exceptions import InvalidPassword


class PasswordService:
    def __init__(self) -> None:
        self._hasher = PasswordHasher()

    def validate_strength(self, password: str) -> None:
        if len(password) < 10:
            raise InvalidPassword("password must be at least 10 characters")
        if password.strip() != password:
            raise InvalidPassword("password must not start or end with whitespace")

    def hash_password(self, password: str) -> str:
        self.validate_strength(password)
        return self._hasher.hash(password)

    def verify_password(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError):
            return False

