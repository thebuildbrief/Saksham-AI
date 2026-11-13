"""Signed bearer and short-lived WebSocket credentials."""
import base64
import hashlib
import hmac
import json
import secrets
import time
from app.core.config import secret_value, settings

_ITERATIONS = 310_000


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iteration_text, salt_text, digest_text = encoded.split("$", 3)
        iterations = int(iteration_text)
        if scheme != "pbkdf2_sha256" or not 100_000 <= iterations <= 2_000_000:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _b64decode(salt_text), iterations)
        return hmac.compare_digest(digest, _b64decode(digest_text))
    except (ValueError, TypeError):
        return False


def _sign(payload: dict) -> str:
    header = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header}.{body}".encode("ascii")
    signature = hmac.new(secret_value(settings.JWT_SECRET_KEY).encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64encode(signature)}"


def _decode(token: str):
    try:
        header_part, payload_part, signature_part = token.split(".")
        header = json.loads(_b64decode(header_part))
        if header != {"alg": "HS256", "typ": "JWT"}:
            return None
        signing_input = f"{header_part}.{payload_part}".encode("ascii")
        expected = hmac.new(secret_value(settings.JWT_SECRET_KEY).encode("utf-8"), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64decode(signature_part)):
            return None
        payload = json.loads(_b64decode(payload_part))
        if not isinstance(payload.get("sub"), str) or int(payload.get("exp", 0)) <= int(time.time()):
            return None
        return payload
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def create_access_token(user_id: str) -> str:
    now = int(time.time())
    return _sign({"sub": user_id, "iat": now, "exp": now + settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, "scope": "access"})


def decode_access_token(token: str):
    payload = _decode(token)
    if not payload or payload.get("scope", "access") != "access":
        return None
    return payload["sub"]


def create_interview_socket_token(user_id: str, session_id: str) -> str:
    now = int(time.time())
    return _sign({"sub": user_id, "session_id": session_id, "iat": now, "exp": now + 120, "scope": "interview:socket"})


def decode_interview_socket_token(token: str):
    payload = _decode(token)
    if not payload or payload.get("scope") != "interview:socket" or not isinstance(payload.get("session_id"), str):
        return None
    return {"user_id": payload["sub"], "session_id": payload["session_id"]}
