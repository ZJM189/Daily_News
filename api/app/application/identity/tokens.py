import hmac
from hashlib import sha256
from secrets import token_urlsafe


def generate_session_token() -> str:
    return token_urlsafe(48)


def hash_session_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def hash_ip_address(ip_address: str | None, secret: str) -> str | None:
    if not ip_address:
        return None
    return hmac.new(secret.encode("utf-8"), ip_address.encode("utf-8"), sha256).hexdigest()
