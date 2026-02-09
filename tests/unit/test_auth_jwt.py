from __future__ import annotations

from datetime import timedelta

from backend.auth import create_access_token, hash_password, verify_password, verify_token


def test_password_hash_and_verify() -> None:
    pw = "StrongPass123"
    pw_hash = hash_password(pw)
    assert pw_hash != pw
    assert verify_password(pw, pw_hash) is True
    assert verify_password("wrong", pw_hash) is False


def test_jwt_token_roundtrip() -> None:
    token = create_access_token({"sub": "alice", "role": "user"})
    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == "alice"
    assert payload["role"] == "user"


def test_jwt_token_tamper_rejected() -> None:
    token = create_access_token({"sub": "alice"})
    parts = token.split(".")
    assert len(parts) == 3
    # 篡改 payload 段
    parts[1] = parts[1][::-1]
    bad = ".".join(parts)
    assert verify_token(bad) is None


def test_jwt_token_expired_rejected() -> None:
    token = create_access_token({"sub": "alice"}, expires_delta=timedelta(seconds=-1))
    assert verify_token(token) is None
