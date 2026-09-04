import base64
import hashlib

from cryptography.fernet import Fernet


class SecretCipher:
    def __init__(self, encryption_key: str) -> None:
        digest = hashlib.sha256(encryption_key.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, encrypted_value: str) -> str:
        return self._fernet.decrypt(encrypted_value.encode("utf-8")).decode("utf-8")


def mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"
